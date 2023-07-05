const coursePrefixInput = document.getElementById("coursePrefix");
const courseTitleInput = document.getElementById("courseTitle");
const resultDiv = document.getElementById("result");
const results = document.getElementById("result_container");
const searchButton = document.querySelector("button[type='submit']");
const spinner = document.getElementById("spinner");
const errorElement = document.getElementById('error');

let resultDisplayed = false;

async function searchCourseSubject() {  
    const coursePrefix = coursePrefixInput.value.trim();
    const courseTitle = courseTitleInput.value.trim();
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
            fetch("http://localhost:5000/api/course_subject", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
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
        <p class="result-line">Similarity Rate: ${similarityRate.toFixed(2)}</p><ol>
    `;  
        resultDiv.style.display = "block";
        resultDisplayed = true;
    } catch (error) {
        console.error(error);
        errorElement.textContent = "An error occurred while fetching the course subject. Please try again later.";
        errorElement.style.display = "block";
        result_container.style.display = "none";
    } finally {
        // Hide the spinner
        spinner.style.visibility = "hidden";
        searchButton.disabled = false;
        result_container.style.display = "block";  
    }
}

async function fetchCourseTitles(coursePrefix) {
    if (!coursePrefix) {
        return;
    }

    // Show loading element
    document.getElementById("loading").style.display = "block";

    try {
        const response = await fetch(
            `http://localhost:5000/api/course_titles?course_prefix=${coursePrefix}`
        );

        if (!response.ok) {
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
        errorElement.textContent = "An error occurred while fetching the course titles. Please try again later.";
        errorElement.style.display = "block";
        result_container.style.display = "none";
    } finally {
        // Hide loading element
        document.getElementById("loading").style.display = "none";
    }
}

async function fetchCoursePrefixes(query) {
    if (!query) {
        return;
    }

    // Show loading element
    document.getElementById("loading").style.display = "block";

    try {
        const response = await fetch(
            `http://localhost:5000/api/course_prefixes?query=${query}`
        );

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        const coursePrefixes = data.course_prefixes;

        const coursePrefixList = document.getElementById("coursePrefixList");
        coursePrefixList.innerHTML = ""; // clear existing options

        // Populate new options
        for (let prefix of coursePrefixes) {
            let option = document.createElement("option");
            option.value = prefix;
            coursePrefixList.appendChild(option);
        }
    } catch (error) {
        console.error(error);
        errorElement.textContent = "An error occurred while fetching the course prefixes. Please try again later.";
        errorElement.style.display = "block";
        result_container.style.display = "none";
    } finally {
        // Hide loading element
        document.getElementById("loading").style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", function () {
    var coursesBtn = document.getElementById("coursesBtn");
    var homeBtn = document.getElementById("homeBtn");
    var courseFormContainer = document.getElementById("courseSearchContainer");
    var welcomeMessage = document.getElementById("welcomeMessage");
    


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

document.getElementById("coursePrefix").addEventListener("change", (event) => {
    let coursePrefix = event.target.value;
    fetchCourseTitles(coursePrefix);
});

document.getElementById("courseTitle").addEventListener("change", (event) => {
    fetchCourseTitles(event.target.value);
});