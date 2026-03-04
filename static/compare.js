document.addEventListener("DOMContentLoaded", () => {
    loadJsonFiles();

    document.getElementById("file1").addEventListener("change", () =>
        loadSections("file1", "section1")
    );
    document.getElementById("file2").addEventListener("change", () =>
        loadSections("file2", "section2")
    );

    document.getElementById("section1").addEventListener("change", () =>
        showQA("file1", "section1", "question1", "answer1")
    );
    document.getElementById("section2").addEventListener("change", () =>
        showQA("file2", "section2", "question2", "answer2")
    );
});

function loadJsonFiles() {
    fetch("/list_json")
        .then(r => r.json())
        .then(data => {
            fillDropdown("file1", data.files);
            fillDropdown("file2", data.files);
        });
}

function fillDropdown(id, items) {
    const sel = document.getElementById(id);
    sel.innerHTML = `<option value="">Select JSON file</option>`;
    items.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f;
        opt.textContent = f;
        sel.appendChild(opt);
    });
}

function loadSections(fileSelectId, sectionSelectId) {
    const filename = document.getElementById(fileSelectId).value;
    const sectionDropdown = document.getElementById(sectionSelectId);

    if (!filename) {
        sectionDropdown.innerHTML = `<option value="">drop down to select section</option>`;
        return;
    }

    fetch(`/json?file=${filename}`)
        .then(r => r.json())
        .then(data => {
            const sections = [];
            Object.values(data.pages).forEach(pageEntries => {
                pageEntries.forEach(entry => {
                    sections.push(entry.section);
                });
            });

            // remove duplicates
            const uniqueSections = [...new Set(sections)];

            sectionDropdown.innerHTML = `<option value="">drop down to select section</option>`;
            uniqueSections.forEach(sec => {
                const opt = document.createElement("option");
                opt.value = sec;
                opt.textContent = sec;
                sectionDropdown.appendChild(opt);
            });
        });
}

function showQA(fileSelectId, sectionSelectId, qId, aId) {
    const filename = document.getElementById(fileSelectId).value;
    const section = document.getElementById(sectionSelectId).value;

    if (!filename || !section) return;

    fetch(`/json?file=${filename}`)
        .then(r => r.json())
        .then(data => {
            let found = null;

            Object.values(data.pages).forEach(pageEntries => {
                pageEntries.forEach(entry => {
                    if (entry.section === section) {
                        found = entry;
                    }
                });
            });

            document.getElementById(qId).textContent = found ? found.question : "";
            document.getElementById(aId).textContent = found ? found.answer : "";
        });
}