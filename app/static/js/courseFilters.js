let sectionLoaded = false;

const changeSection = function(sectionId) {
    var re = /(course)\/(\d+)/gi;
    var url = window.location.href;
    var courseId = re.exec(url)[2];

    // Set a reload action for the current ID
    document.getElementById("sectionReload").setAttribute('data-section', sectionId);
    let table = document.getElementById('student-table');

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
                    th.setAttribute('data-outcome', assignment['outcome_id']);
                    th.setAttribute('class', 'th-outcome');
                    th.innerText = assignment['assignment_name'];
                    header.appendChild(th);
                })
            }
            
            // Now, build the body of the table
            table.appendChild(document.createElement('tbody'))

            // Grab the body in a var
            let container = document.querySelector("#student-table > tbody")

            // Look for those scores again
            // Append each score to the table
            if(scores) {
                scores.forEach((el) => {
                    var tr = document.createElement('tr');

                    // Set the variable of each row == student[canvas_id]
                    // This makes processing the table easier
                    tr.setAttribute('id', el['canvas_id']);
                    tr.setAttribute('class', 'trow');
                    var name = document.createElement('td');
                    name.innerText = `${el['user_name']}`;
                    tr.appendChild(name);

                    // Loop through the submissions array for each student
                    el['submissions'].forEach((item) => {
                        var td = document.createElement('td');
                        td.setAttribute('data-outcome', item['outcome_id'])
                        td.innerText = `${item['assignment_score']}`;
                        
                        // Display the dash instead of zero if there is no score
                        if(!item['assignment_score']) {
                            td.innerText = '-'
                        }

                        // Append the cell to the row
                        tr.appendChild(td);
                    })

                    // Add that row to the table
                    container.appendChild(tr);
                })
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
    
    var assignmentId = e.target.value;
    var outcomeId = $(e.target)
        .closest("tr")
        .attr("id");
    
        $.ajax({
            type: "POST",
            url: "/align",
            data: JSON.stringify({
            assignment_id: assignmentId,
            outcome_id: outcomeId
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
    var arr = new Array();
    var re = /(course)\/(\d+)/gi;
    var courseId = re.exec(window.location.href)[2];
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
document.getElementById("alignment-table").addEventListener("change", changeHandler, false);
document.getElementById("section").addEventListener("change", function(e) {
    var sectionId = e.target.value;
    changeSection(sectionId);
});

$("#sectionReload").on('click', function(e) {
    var sectionId = $(this).data('section');
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