let sectionLoaded = false;

const getCourseId = function() {
    var re = /(course)\/(\d+)/gi;
    var url = window.location.href;
    var courseId = re.exec(url)[2];
    return courseId;
}

const getSectionAssignments = function(sectionId) {

    const courseId = getCourseId();
    const assignmentSelect = document.querySelector('#rubric-assignment-select');

    $.ajax({
        type: 'GET',
        url: `../course/${courseId}/assignments`,
        success: function(result) {

            for(var r=0; r<result.success.length; r++) {
                let option = document.createElement('option');
                option.value = result.success[r].id;
                option.innerText = result.success[r].name;
                assignmentSelect.appendChild(option);
            }
        }
    })
}

const getAssignmentRubrics = function(courseId, assignmentId) {

    $.ajax({
        type: 'GET',
        url: `../course/${courseId}/assignments/${assignmentId}/rubric`,
        success: function(result) {
            result = result.data;
            const table = document.querySelector('#student-rubric-table');
            table.innerHTML = ''; // Empty the table

            let thead = document.createElement('thead');
            let row = document.createElement('tr');

            thead.appendChild(row);
        
            table.appendChild(thead);
        
            let header = document.querySelector('#student-rubric-table > thead > tr')
            header.appendChild(document.createElement('th'));
            header.firstElementChild.innerText = "Student";
            header.appendChild(document.createElement('th'));
            header.lastElementChild.innerText = "Score";

            // Add a header column in the table
            result.columns.forEach(function(el) {
                var th = document.createElement('th');
                th.setAttribute('data-outcome', el['id']);
                th.setAttribute('class', 'th-outcome');
                th.innerText = el['name'];
                header.appendChild(th);
            })

            table.appendChild(document.createElement('tbody'))

            let container = document.querySelector('#student-rubric-table > tbody');

            result.studentResults.forEach(function(student) {
                // Set the variable of each row == student[canvas_id]
                // This makes processing the table easier
                let rubric = student.rubric;
                let tr = document.createElement('tr');
                tr.setAttribute('id', student['id']);
                tr.setAttribute('class', 'trow');
                var name = document.createElement('td');
                var score = document.createElement('td');
                name.innerText = `${student['name']}`;
                score.innerText = `${student['score']}`
                tr.appendChild(name);
                tr.appendChild(score);

                // Loop through the submissions array for each student
                result.columns.forEach((item) => {
                    console.log(rubric)
                    var td = document.createElement('td');
                    td.setAttribute('data-outcome', item['id'])
                    if(student.rubric && rubric[item['id']]['points']) {
                        td.innerText = `${rubric[item['id']]['points']}`;
                    } else {
                        td.innerText = ' - '
                    }

                    // Append the cell to the row
                    tr.appendChild(td);
                })

                // Add that row to the table
                container.appendChild(tr);
            })
        }
    })
    



}

const changeSection = function(sectionId) {
    
    courseId = getCourseId();

    // Set a reload action for the current ID
    document.querySelector("#sectionReload").setAttribute('data-section', sectionId);
    let table = document.querySelector('#student-table');

    // Clear the inside of the table for a clean reload
    table.innerHTML = "";

    $.ajax({
        type: "POST",
        url: "/section",
        data: JSON.stringify({
        course_id: courseId,
        section_id: sectionId,
        }),
        contentType: "application/json;charset=UTF-8",
        success: function(scores) {

            // When the data comes back in enable the reload button
            sectionLoaded = true;

            if(sectionLoaded) {
                $("#sectionReload").attr('disabled', false);
            }

            // If there are scores returned, rebuild the table
            if(scores) {
                // Start with the table header
                let thead = document.createElement('thead');
                let row = document.createElement('tr');
                thead.appendChild(row);
                table.appendChild(thead)

                // Grab the header to append column headings
                var header = document.querySelector('#student-table > thead > tr')
                header.appendChild(document.createElement('th'));
                header.firstElementChild.innerText = "Student";

                // Loop through the first submission object to get the Assignment titles
                // This is hacky, but it works.
                scores[0]['submissions'].forEach((assignment) => {
                    var th = document.createElement('th');
                    var outcomeId = Object.keys(assignment)
                    th.setAttribute('data-outcome', outcomeId);
                    th.setAttribute('class', 'th-outcome');
                    th.innerText = assignment[outcomeId]['assignment_name'];
                    header.appendChild(th);
                })
            }
            
            // Now, build the body of the table
            table.appendChild(document.createElement('tbody'))

            // Grab the body in a var
            let container = document.querySelector("#student-table > tbody")
            let headers = document.querySelectorAll("#student-table > thead > tr > th");

            if(scores) {
                scores.forEach((student) => {
                    var tr = document.createElement('tr');

                    tr.setAttribute('id', student['canvas_id']);
                    tr.setAttribute('class', 'trow');
                    var name = document.createElement('td');
                    name.innerText = `${student['user_name']}`;
                    tr.appendChild(name);

                    // Use the headers to index the submissions cells to
                    // make sure the correct score is in the correct column.
                    headers.forEach((header) => {
                        if(header.dataset.outcome) {
                            let submissions = student.submissions;
                            let outcome = header.dataset.outcome;
                            var td = document.createElement('td');
                            td.setAttribute('data-outcome', outcome);
                            var score = submissions.find(item => Object.keys(item) == outcome)
                            score = (score[outcome]['assignment_score'] === null) ? `-` : score[outcome]['assignment_score'];
                            td.innerText = score
    
                            tr.appendChild(td);
                        }
                    })
                    container.appendChild(tr);
                });

            } else {
                let row = document.createElement('tr');
                let msg = document.createElement('td');
    
                msg.innerText = 'Please align an outcome in the Alignments tab';
                row.appendChild(msg);
                container.appendChild(row);
            }
        }, error: function(request, status, message) {
            let container = document.querySelector(".msg");
            console.log(request.responseJSON.message);
            let row = document.createElement('tr');
            let msg = document.createElement('td');

            msg.innerText = request.responseJSON.message;
            row.appendChild(msg);
            container.appendChild(row);
        }
    })
}

const changeHandler = function(e) {
    var elem = e;

    // if(!sectionLoaded) {
    //     $("#sectionReload").css('display', 'none');
    // } else {
    //     $("#sectionReload").css('display', 'block');
    // }

    var courseId = getCourseId();
    var assignmentId = e.target.value;
    var outcomeId = $(e.target)
        .closest("tr")
        .attr("id");
    
        $.ajax({
            type: "POST",
            url: "/align",
            data: JSON.stringify({
            assignment_id: assignmentId,
            outcome_id: outcomeId,
            course_id: courseId,
        }),
        contentType: "application/json;charset=UTF-8",
        success: function(resp) {
            console.log(resp.success)
            var id = resp.success[0];
        
            $(`#${id} td:last`)
                .animate(
                {
                    opacity: 1
                },
                100
                )
                .animate(
                {
                    opacity: 0
                },
                2000
                );
            
            // setTimeout(location.reload(true), 2200);
        },
        failure: function(resp) {
            console.error(resp);
        }
    });
};


const processTable = function() {
    
    var courseId = getCourseId();
    var arr = new Array();
    var outcomeId = new Array();

    // Collect specific outcome IDs
    // https://community.canvaslms.com/thread/36750
    $('th.th-outcome').each(function(i, el) {
        var head = $(el);
        outcomeId.push(head.data("outcome"));
    })

    $("tr.trow").each(function(i, el) {
        var row = $(el);
        var studentId = row.attr("id");
        arr.push(studentId);
    });

    $.ajax({
        type: "POST",
        url: "/outcomes",
        data: JSON.stringify({
        student_id_list: arr,
        course_id: courseId,
        outcome_id_list: outcomeId
        }),
        contentType: "application/json",
        success: function(resp) {
            console.log(resp);
            for (var i = 0; i < resp.success.length; i++) {
                var student = resp.success[i];

                var studentId = student.student_id;
                var array = student.outcomes;

                $(`#${studentId}`)
                .children("td")
                .each(function(i, el) {
                    console.log(el)
                    array.filter(function(item) {
                        if ($(el).attr("data-outcome") == item.outcome_id) {
                            console.log(item)
                            $(el).html(item.assignment_score);
                        }
                    });
                }); 
            }
        },
        failure: function(resp) {
        console.log(resp);
        }
    });
};

// Set the event listeners
document.querySelector("#alignment-table").addEventListener("change", changeHandler, false);
document.querySelector("#section").addEventListener("change", function(e) {
    var sectionId = e.target.value;
    changeSection(sectionId);
});

document.querySelector("#rubric-section").addEventListener("change", function(e) {
    const sectionId = e.target.value;
    getSectionAssignments(sectionId)
})

document.querySelector("#rubric-assignment-select").addEventListener("change", function(e) {
    // const sectionId = document.querySelector("#rubric-section").value;
    const courseId = getCourseId()
    const assignmentId = e.target.value;

    getAssignmentRubrics(courseId, assignmentId);
})

document.querySelector("#sectionReload").addEventListener('click', function(e) {
    var sectionId = this.dataset.section;
    changeSection(sectionId);
})

// Toggle the loader animation
$(document).ajaxStart(function() {
    console.log("started ajax");
    $(".loader-wrap").show();
});

$(document).ajaxStop(function() {
    console.log("stopped ajax");
    $(".loader-wrap").hide();
});