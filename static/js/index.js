const coursePrefixInput = document.getElementById("coursePrefix");
const courseTitleInput = document.getElementById("courseTitle");
const universityInput = document.getElementById("university");
const resultDiv = document.getElementById("result");
const results = document.getElementById("result_container");
const searchButton = document.getElementById("searchButton");
const spinner = document.getElementById("spinner");
const errorElement = document.getElementById('error');
const loader = document.getElementById("loading");

const serverAddress = "http://127.0.0.1:5000";

let resultDisplayed = false;

async function searchCourseSubject() {  
    const coursePrefix = coursePrefixInput.value.trim();
    const courseTitle = courseTitleInput.value.trim();
    const university = universityInput.value.trim();

    if (coursePrefix==""){
        errorElement.textContent = "Please enter the course prefix";
        errorElement.style.display = "block";
        return;
    }else if(courseTitle==""){
        errorElement.textContent = "Please enter the course title";
        errorElement.style.display = "block";
        return;     
    }
    if (resultDisplayed) {
        resultDiv.innerHTML = "";
        resultDisplayed = false;
    }

    // Set the spinner visibility to visible
    spinner.style.visibility = "visible";
    searchButton.disabled = true;
    result_container.style.display = "none";
    errorElement.style.display = "none";
    try {
        const response = await Promise.race([
            fetch(`${serverAddress}/api/course_subject`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    university: university,
                    course_prefix: coursePrefix,
                    course_title: courseTitle,
                }),
            }),
        ]);

        // Hide the spinner
        spinner.style.visibility = "hidden";
        searchButton.disabled = false;
        result_container.style.display = "block";

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        const courseSubject = data.course_subject;
        const similarityRate = data.similarity_rate;
        const deptNames = data.department_abbreviations;

        resultDiv.innerHTML = `
        <h4 class="result-line">Course Subject: ${courseSubject}</h4>
        <p class="result-line">Department: ${deptNames}</p>
    `;  
        resultDiv.style.display = "block";
        resultDisplayed = true;

    } catch (error) {
        console.error(error);
        errorElement.textContent = "An error occurred while fetching the course subject. Please refresh the page and try again.";
        errorElement.style.display = "block";
        result_container.style.display = "none";
    } finally {
        // Hide the spinner
        spinner.style.visibility = "hidden";
        searchButton.disabled = false;
        result_container.style.display = "block";  
    }
}

// Define custom error type
class UniversityNotFoundError extends Error {
    constructor(message) {
        super(message);
        this.name = "UniversityNotFoundError";
    }
}
class TitleNotFoundError extends Error {
    constructor(message) {
        super(message);
        this.name = "TitleNotFoundError";
    }
}
let universitySearchCompleted = false;
async function fetchUniversity(query) {
    if (!query) {
        return;
    }
    errorElement.style.display = "none";
    try {
        const response = await fetch(`${serverAddress}/api/university?query=${query}`);
        const data = await response.json();
        if (!response.ok || data.university.length === 0) {
            coursePrefixInput.disabled = true;
            courseTitleInput.disabled = true;
            if (universitySearchCompleted) { // Only throw the error if the user has finished typing
                throw new UniversityNotFoundError('University not found');
            }
            return;
        }

        const universityList = document.getElementById("universityList");
        universityList.innerHTML = ""; // clear existing options

        // Populate new options
        for (let univ of data.university) {
            let option = document.createElement("option");
            option.value = univ;
            universityList.appendChild(option);
        }

        // Call fetchCoursePrefixes only if fetchUniversity is successful
    } catch (error) {
        console.error(error);
        if (error instanceof UniversityNotFoundError) {
            errorElement.textContent = error.message;
        } else {
            errorElement.textContent = "An error occurred while fetching the university. Please refresh the page and try again.";
        }
        errorElement.style.display = "block";
        result_container.style.display = "none";
        loader.style.display = "none";
    } finally {
        // Hide loading element
        loader.style.display = "none";    
    }
}
class CoursePrefixNotFoundError extends Error {
    constructor(message) {
        super(message);
        this.name = "CoursePrefixNotFoundError";
    }
}
let prefixSearchCompleted = false;
async function fetchCoursePrefixes(university, coursePrefix = null) {
    if (!university) {
        return; // exit early if no university
    }
    loader.textContent = "Loading the Course prefix..."
    loader.style.display = "block";
    coursePrefixInput.disabled = true;
    errorElement.style.display = "none";
    try {
        let url = `${serverAddress}/api/course_prefix?university=${university}`;
        if (coursePrefix) url += `&course_prefix=${coursePrefix}`; 
        
        const response = await fetch(url);
        const data = await response.json();
        loader.textContent = "Loading the Course Prefixes..."
        loader.style.display = "block";
        coursePrefixInput.disabled = true;

        if (!response.ok || data.course_prefix.length === 0) {
            if (prefixSearchCompleted) { // Only throw the error if the user has finished typing
                throw new CoursePrefixNotFoundError('Course prefix not found');
            }
            return;
        }

        const coursePrefixes = data.course_prefix;

        const coursePrefixList = document.getElementById("coursePrefixList");
        coursePrefixList.innerHTML = ""; // clear existing options

        // Populate new options
        for (let prefix of data.course_prefix) {
            let option = document.createElement("option");
            option.value = prefix;
            coursePrefixList.appendChild(option);
        }

        // Call fetchCourseTitles only if fetchCoursePrefixes is successful
        await fetchCourseTitles(university, coursePrefix);
        loader.textContent = "Loading the Course Title..."
        loader.style.display = "block";
    } catch (error) {
        console.error(error);
        if (error instanceof CoursePrefixNotFoundError) {
            errorElement.textContent = error.message;
        } else {
            errorElement.textContent = "An error occurred while fetching the course prefixes. Please refresh the page and try again.";
        }
        errorElement.style.display = "block";
        result_container.style.display = "none";
        loader.style.display = "none";
    } finally {
        // Hide loading element
        loader.style.display = "none";
        coursePrefixInput.disabled = false;
    }
}

class CourseTitleNotFoundError extends Error {
    constructor(message) {
        super(message);
        this.name = "CourseTitleNotFoundError";
    }
}

async function fetchCourseTitles(university, coursePrefix) {
    if (!university || !coursePrefix) {
        return;
    }
    courseTitleInput.disabled = true;
    loader.textContent = "Loading the Course Title..."
    loader.style.display = "block";
    errorElement.style.display = "none";
    try {
        const response = await fetch(
            `${serverAddress}/api/course_titles?university=${encodeURIComponent(university)}&course_prefix=${encodeURIComponent(coursePrefix)}`
        );
        // Show loading element
        loader.textContent = "Loading the Course Titles..."
        loader.style.display = "block";

        if (!response.ok) {
            coursePrefixInput.disabled=true;
            courseTitleInput.disabled=true; // disable the Course Title input box
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        const courseTitles = data.course_titles;

        const courseTitleList = document.getElementById("courseTitleList");
        courseTitleList.innerHTML = ""; // clear existing options

        // Populate new options
        for (let title of courseTitles) {
            let option = document.createElement("option");
            option.value = title;
            courseTitleList.appendChild(option);
        }
    } catch (error) {
        console.error(error);
        if (error instanceof CourseTitleNotFoundError) {
            errorElement.textContent = error.message;
        } else {
            errorElement.textContent = "An error occurred while fetching the course titles. Please refresh the page and try again.";
        }
        errorElement.style.display = "block";
        result_container.style.display = "none";
    } finally {
        // Hide loading element
        loader.style.display = "none";
        courseTitleInput.disabled = false;
    }
}
function debounce(func, delay) {
    let debounceTimer;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => func.apply(context, args), delay);
    }
}
document.addEventListener("DOMContentLoaded", function () {
    var coursesBtn = document.getElementById("coursesBtn");
    var homeBtn = document.getElementById("homeBtn");
    var courseFormContainer = document.getElementById("courseSearchContainer");
    var welcomeMessage = document.getElementById("welcomeMessage");

    document.getElementById('university').addEventListener('input', debounce(function(e) {
        universitySearchCompleted = false; // Reset the flag when the user types
        fetchUniversity(e.target.value);
    }, 500)); // delay of 300ms
    document.getElementById('university').addEventListener('change', function(e) {
        universitySearchCompleted = true; // Reset the flag when the user types
        fetchCoursePrefixes(e.target.value);
    });
    document.getElementById('coursePrefix').addEventListener('input', debounce(function(e) {
        prefixSearchCompleted = false; // Reset the flag when the user types
        fetchCoursePrefixes(e.target.value);
    }, 300)); // delay of 300ms
    document.getElementById('coursePrefix').addEventListener('change', function(e) {
        prefixSearchCompleted = true;
        fetchCourseTitles(document.getElementById('university').value, e.target.value);
    });

    document.getElementById('searchButton').addEventListener('click', function(e) {
        e.preventDefault();
        searchCourseSubject();
    });

    coursesBtn.addEventListener("click", function () {
        coursesBtn.classList.add("active");
        homeBtn.classList.remove("active");
        courseFormContainer.style.display = "block";
        welcomeMessage.style.display = "none";
    });


    homeBtn.addEventListener("click", function () {
        homeBtn.classList.add("active");
        coursesBtn.classList.remove("active");
        courseFormContainer.style.display = "none";
        welcomeMessage.style.display = "block";
        document.getElementById("result").style.display = "none";
        
    });

});

// Attach event listeners
document.getElementById("hereBtn").addEventListener("click", (event) => {
    event.preventDefault();
    var coursesBtn = document.getElementById("coursesBtn");
    var homeBtn = document.getElementById("homeBtn");
    var courseFormContainer = document.getElementById("courseSearchContainer");
    var welcomeMessage = document.getElementById("welcomeMessage");

    coursesBtn.classList.add("active");
    homeBtn.classList.remove("active");
    courseFormContainer.style.display = "block";
    welcomeMessage.style.display = "none";
});
document.getElementById("logo_btn").addEventListener("click", (event) => {
    event.preventDefault();
    var coursesBtn = document.getElementById("coursesBtn");
    var homeBtn = document.getElementById("homeBtn");
    var courseFormContainer = document.getElementById("courseSearchContainer");
    var welcomeMessage = document.getElementById("welcomeMessage");

    homeBtn.classList.add("active");coursesBtn
    coursesBtn.classList.remove("active");
    courseFormContainer.style.display = "none";
    welcomeMessage.style.display = "block";
});