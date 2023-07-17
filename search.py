# Import required libraries
from sentence_transformers import SentenceTransformer
import torch
import re
import psycopg2
from rapidfuzz import fuzz, process
import atexit
import psycopg2.pool
from config import config  # import the config object
from autocorrect import Speller

# Load pre-trained model
model = SentenceTransformer('paraphrase-MiniLM-L3-v2')

# Define function to get sentence embedding using pre-trained model
def get_sentence_embeddings(sentences):
    return model.encode(sentences, convert_to_tensor=True)

# Global variables for storing data fetched from the database
subject_list = None
abbreviations = None

# Define function to replace abbreviations in a given sentence using a dictionary of abbreviations
def replace_abbreviations(course_title, abbreviations):
    words = course_title.split()
    expansions = [[]]
    for i, word in enumerate(words):
        if word in abbreviations:
            new_expansions = []
            for expansion in expansions:
                new_expansion = expansion + [abbreviations[word]]
                new_expansions.append(new_expansion)
            expansions = new_expansions  # Replacing old expansions with new ones
            print(f"Expanded {word} to {abbreviations[word]}")  # Printing the expanded abbreviation
        else:
            for expansion in expansions:
                expansion.append(word)
    return [' '.join(expansion) for expansion in expansions]

# Define function to check if a course is a foreign language course based on a list of keywords
def is_foreign_language_course(course_title, subject_list):
    foreign_language_keywords = fetch_foreign_language_from_database()

    for keyword in foreign_language_keywords:
        if keyword.lower() in course_title.lower():
            # Check if the keyword matches an existing subject
            for subject in subject_list:
                if keyword.lower() == subject.lower():
                    return subject
            # If no match found in subject_list, return 'Foreign Language'
            return "Foreign Language"
    return None

# Define function to expand department prefix using a dictionary of abbreviations
def expand_dept_prefix(course_prefix, dept_abbreviations):
    dept_prefix = ''.join([char for char in course_prefix if char.isalpha()])
    return dept_abbreviations.get(dept_prefix.lower(), dept_prefix.title())

# Define function to remove trailing non-numeric characters from a string
def remove_trailing_non_numerics(prefix):
    while prefix and not prefix[-1].isdigit():
        prefix = prefix[:-1]
    return prefix

# Define function to find the matching subject in a list based on course title
def get_matching_subject(course_title, subject_list):
    best_match = process.extractOne(course_title, subject_list)
    return best_match[0] if best_match[1] > 90 else None # 80 is the confidence score, adjust as needed

# Define function to match subject using department names fetched from the database and a list of subjects
def match_subject_with_dept(dept_names, subject_list):
    highest_similarity = -1
    matched_subject = "Special Topics"
    # Convert subject_list to lowercase
    lower_subject_list = [subject.lower() for subject in subject_list]

    for dept in dept_names:
        # Convert department name to lowercase
        lower_dept = dept.lower()
  
        # Check if the dept is a foreign language course
        foreign_language_subject = is_foreign_language_course(dept, subject_list)
        if foreign_language_subject is not None:
            return foreign_language_subject, 1.0

        # Check for an exact match first
        if lower_dept in lower_subject_list:
            print("Exact match found for the dept")
            return dept.title(), 1.0  # Return the title-cased department name
        # If there's no exact or partial match, compute the semantic similarity
        dept_embedding = get_sentence_embeddings(dept)
        subject_embeddings = torch.stack([get_sentence_embeddings(subject) for subject in subject_list])

        similarities = torch.nn.functional.cosine_similarity(dept_embedding, subject_embeddings)

        index = torch.argmax(similarities)
        similarity = similarities[index]

        if similarity.item() > highest_similarity:
            highest_similarity = similarity.item()
            matched_subject = subject_list[index]

    return matched_subject, highest_similarity

def exclude_subjects(course_title, subjects):
    excluded_subjects = fetch_excluded_subjects_from_database()
    # Convert course title and excluded_combinations to lowercase for case-insensitive comparison
    lower_course_title = course_title.lower()
    lower_excluded_combinations = {k.lower(): v.lower() for k, v in excluded_subjects.items()}

    # Remove the excluded subjects from the list if the course title contains a key in excluded_combinations
    for exclusion_key, exclusion_value in lower_excluded_combinations.items():
        if exclusion_key in lower_course_title:
            subjects = [subject for subject in subjects if subject.lower() != exclusion_value]

    # Return the filtered list of subjects
    return subjects

# Define function to match subject using course title, course prefix, a list of subjects and a dictionary of abbreviations
def match_subject_by_title(course_title, course_prefix, university, subject_list, abbreviations, threshold=0.55, debug=False):
    # Initialise the spell checker
    spell = Speller(lang='en')
    course_title = ' '.join([spell(word) for word in course_title.split()])
    course_title = course_title.title()
    lower_title = course_title.lower()

    predefined_subjects = fetch_predefined_subjects_from_database()
    science_keywords = fetch_science_keywords_from_database()
    keyword_to_subject = fetch_keyowrd_subjects_from_database()
    excluded_words = [word.lower() for word in fetch_excluded_words_from_database()]
    excluded_titles = fetch_excluded_titles_from_database()
    dept_names = fetch_dept_abbreviations_from_database(university,course_prefix)
    # Exclude certain subjects based on the course title
    subject_list = exclude_subjects(course_title, subject_list)

    # If the course title is in the list of excluded titles, return a special result
    if course_title.lower() in excluded_titles:
        return f"Title excluded: {course_title}", 0.0
  
    # Calculate embeddings only for the subjects that are not excluded
    subject_embeddings = torch.stack([get_sentence_embeddings(subject) for subject in subject_list])

    # Check for keyword subjects
    for keyword, subject in keyword_to_subject.items():
        if re.search(keyword, lower_title):
            if debug: print(f'Matched by regex: {subject}')
            return subject, 1.0

    # First, convert the course title to lowercase and remove excluded words
    course_title = re.sub(r'\((.*?)\)', r'\1', course_title)
    course_title = course_title.title()
    course_title = course_title.replace('/', ' / ')
    # Course title words converted to lowercase for comparison
    filtered_title = ' '.join([word for word in course_title.split() if word.lower() not in excluded_words])
    if not filtered_title:
        if debug: print('Course title consisted only of excluded words.')
        # Match department
        matched_subject, highest_similarity = match_subject_with_dept(dept_names, subject_list)
        print(f'After excluding excluded words matched with dept: ',matched_subject)
        return matched_subject, highest_similarity
    
    # Check if the course title and department match a predefined combination
    for (dept, title), subject in predefined_subjects.items():
        if dept.lower() == '' and re.search(title, filtered_title.lower()):
            return subject, 1.0

        elif dept.lower() in [d.lower() for d in dept_names] and re.search(title, filtered_title):
            return subject, 1.0
        
    # If 'Edu' is in the department, categorize courses accordingly
    if 'Edu' in course_prefix:
        is_teaching_science = any(keyword in lower_title for keyword in science_keywords)
        if is_teaching_science:
            if debug: print(f'Matched by Edu prefix (Teaching Science): Teaching Science')
            return 'Teaching Science', 1.0
        else:
            if debug: print(f'Matched by Edu prefix (Education): Education')
            return 'Education', 1.0

    # Expand course title abbreviations
    expanded_titles = replace_abbreviations(filtered_title, abbreviations)

    highest_similarity = -1
    matched_subject = "Special Topics"

    # Check if the course title is a foreign language course
    foreign_language_subject = is_foreign_language_course(filtered_title, subject_list)
    if foreign_language_subject is not None:
        return foreign_language_subject, 1.0
 
    # Check for predefined subjects using regex patterns
    for expanded_title in expanded_titles:
        # Remove excluded words from expanded title
        lower_title = expanded_title.lower()
        course_title_embedding = get_sentence_embeddings(expanded_title)
        # Compute cosine similarity between course title and subjects
        similarities = torch.nn.functional.cosine_similarity(course_title_embedding, subject_embeddings)
        
        index = torch.argmax(similarities)
        similarity = similarities[index]

        if similarity.item() > highest_similarity:
            highest_similarity = similarity.item()
            print(f'Similarity found: ', highest_similarity)
            matched_subject = subject_list[index]

        if highest_similarity < threshold and highest_similarity > 0.50:
            # Check for an exact match after applying all the existing logic
            for word in expanded_title.split():
                if word not in excluded_words:
                    exact_match = get_matching_subject(word, subject_list)
                    if exact_match is not None and exact_match != matched_subject:
                        print('Partial match found: ',exact_match)
                        if debug: print(f'Exact match found: {exact_match}')
                        return exact_match, 1.0
        if debug: print(f'Matched by highest_similarity: {matched_subject}')

    return matched_subject, highest_similarity
# Create a connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    1,  # minconn
    10,  # maxconn
    host=config.DB_HOST,
    database=config.DB_NAME,
    user=config.DB_USERNAME,
    password=config.DB_PASSWORD
)
# Function to get connection from the pool
def fetch_from_database():
    return db_pool.getconn()

# Function to return connection back to the pool
def return_to_pool(conn):
    db_pool.putconn(conn)
# Function to close the connection pool
def close_all_conn():
    psycopg2.pool.SimpleConnectionPool.closeall()

def fetch_university_from_database(university):
    # Implement your database query here
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT name FROM dept_abbreviations WHERE LOWER(name) LIKE LOWER(%s)", (university+'%',))
        university = [row[0] for row in cursor.fetchall()]
        if not university or university == [''] or university is None:
            raise ValueError('University not found')
    except Exception as e:
        print(f"An error occurred while fetching university: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return university

def fetch_course_prefix_from_database(university, course_prefix):
    # Implement your database query here
    connection = fetch_from_database()

    # Handle if university or course_prefix is None
    university = university if university is not None else ''
    course_prefix = course_prefix if course_prefix is not None else ''

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT courses FROM dept_abbreviations WHERE LOWER(name) LIKE LOWER(%s) AND LOWER(courses) LIKE LOWER(%s)", (university+'%', course_prefix+'%'))
        course_prefixes = [row[0] for row in cursor.fetchall()]
        # Throw an error if no course prefix is found
        if not course_prefixes or course_prefixes == [''] or course_prefixes is None:
            raise ValueError('Course prefix not found')
    except Exception as e:
        print(f"An error occurred while fetching course prefix: {e}")
        raise e
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return course_prefixes

def fetch_course_titles_from_database(university, course_prefix):
    connection = fetch_from_database()

    # Handle if university or course_prefix is None
    university = university if university is not None else ''
    course_prefix = course_prefix if course_prefix is not None else ''

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT course_title FROM dept_abbreviations WHERE LOWER(name) LIKE LOWER(%s) AND LOWER(courses) LIKE LOWER(%s)", (university+'%', course_prefix+'%'))
        course_titles = [row[0] for row in cursor.fetchall()]
        # Throw an error if no course prefix is found
        if not course_titles or course_titles == [''] or course_titles is None:
            raise ValueError('Course title not found')
    except Exception as e:
        print(f"An error occurred while fetching course_title: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return course_titles

def fetch_subject_list_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT subject_list FROM subjects")

        subject_list = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"An error occurred while fetching subject_list: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return subject_list

def fetch_dept_abbreviations_from_database(university,course_prefix):
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        # Using ILIKE with a wildcard character (%) to match courses that start with the course_prefix
        cursor.execute("SELECT DISTINCT departments FROM dept_abbreviations WHERE LOWER(name) LIKE LOWER(%s) AND LOWER(courses) LIKE LOWER(%s)", ('%'+university+'%', '%'+course_prefix+'%'))
        dept_abbreviations = [row[0] for row in cursor.fetchall()]  # Create a dictionary from the fetched rows
    except Exception as e:
        print(f"An error occurred while fetching dept_abbreviations: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return dept_abbreviations

def fetch_excluded_subjects_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT titles,subjects FROM excluded_subjects")  # Update the SQL query to fetch both keyword and subject
        excluded_subjects = {row[0]: row[1] for row in cursor.fetchall()}  # Create a dictionary from the fetched rows
    except Exception as e:
        print(f"An error occurred while fetching excluded_subjects: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return excluded_subjects

def fetch_keyowrd_subjects_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT keyword, subject FROM keyword_subjects")  # Update the SQL query to fetch both keyword and subject
        keyword_subjects = {row[0]: row[1] for row in cursor.fetchall()}  # Create a dictionary from the fetched rows
    except Exception as e:
        print(f"An error occurred while fetching keyword_subjects: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return keyword_subjects

def fetch_predefined_subjects_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT dept, course_title, subject FROM predefined_subjects")  # Update the SQL query to fetch both keyword and subject
        predefined_subjects = {(row[0], re.compile(r'(?i)' + row[1])): row[2] for row in cursor.fetchall()}
    except Exception as e:
        print(f"An error occurred while fetching predefined_subjects: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return predefined_subjects

def fetch_foreign_language_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT foreign_languages FROM foreign_language_keywords")
        foreign_language_subject = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"An error occurred while fetching foreign_language_keywords: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool 
    return foreign_language_subject

def fetch_abbreviations_from_database():
    connection = fetch_from_database()  
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT abbreviations,subject FROM abbreviation")
        abbreviations = {row[0]: row[1] for row in cursor.fetchall()}  # Create a dictionary from the fetched rows
    except Exception as e:
        print(f"An error occurred while fetching abbreviation: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return abbreviations

def fetch_excluded_words_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT words FROM excluded_words")
        excluded_words = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"An error occurred while fetching excluded_words: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return excluded_words
def fetch_excluded_titles_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT titles FROM excluded_titles")
        excluded_titles = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"An error occurred while fetching excluded_titles: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return excluded_titles
def fetch_science_keywords_from_database():
    connection = fetch_from_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT science_keyword FROM science_keywords")
        science_keywords = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"An error occurred while fetching science_keywords: {e}")
    finally:
        cursor.close()  # close the cursor
        return_to_pool(connection)  # return the connection to the pool
    return science_keywords

def setup():
    global subject_list, abbreviations
    # Fetch the data from the database
    subject_list = fetch_subject_list_from_database()
    abbreviations = fetch_abbreviations_from_database()

def main(course_prefix, course_title, university):
    global subject_list, abbreviations
    
    # Fetch department names from the database
    fetched_dept_names = fetch_dept_abbreviations_from_database(university, course_prefix)

    # Use fetched department for matching
    subject, similarity_rate_title = match_subject_by_title(course_title, course_prefix, university, subject_list, abbreviations)

    output_subject = subject
    similarity_rate = similarity_rate_title
    match_method = "Title"

    # Try the department name-based method only if the title did not match with a high enough similarity rate
    if similarity_rate_title < 0.55:
        output_subject, similarity_rate_dept  = match_subject_with_dept(fetched_dept_names, subject_list)

        # If the highest similarity rate from department name match is still less than 0.55, then the subject should be set to "Special Topics"
        if similarity_rate_dept  < 0.50:
            output_subject = "Special Topics"

        similarity_rate = similarity_rate_dept 
        match_method = "Dept"

    print(f"The course subject for course_title:{course_title} is {output_subject} with a similarity rate of {similarity_rate:.2f}. Matched with {match_method}. Dept:{output_subject} Title:{subject},{similarity_rate_title}")

    return output_subject, similarity_rate, fetched_dept_names[:5]

atexit.register(db_pool.closeall)

if __name__ == "__main__":
    setup()
    while True:  # Keep the application running until it's manually stopped
        university = input("University: ") 
        course_prefix = input("Course Prefix: ")
        course_title = input("Course Title: ")
        main(course_prefix, course_title, university)
