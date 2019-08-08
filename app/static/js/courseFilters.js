const changeSection = function(e) {
    var elem = e;
    var sectionId = e.target.value;
    var re = /(course)\/(\d+)/gi;
    var url = window.location.href;
    var courseId = re.exec(url)[2];

    console.log(courseId, sectionId)

    $.ajax({
        type: "POST",
        url: "/section",
        data: JSON.stringify({
        course_id: courseId,
        section_id: sectionId,
        }),
        contentType: "application/json;charset=UTF-8",
        success: function(resp) {
            console.log(resp)
            
            let container = document.querySelector("#student-table > tbody")

            if(resp) {
                resp.forEach((el) => {
                    var tr = document.createElement('tr');
                    tr.setAttribute('id', el['canvas_id']);
                    tr.setAttribute('class', 'trow');
                    var name = document.createElement('td');
                    name.innerText = `${el['user_name']}`;
                    tr.appendChild(name);

                el['submissions'].forEach((item) => {
                    var td = document.createElement('td');
                    td.setAttribute('data-outcome', item['outcome_id'])
                    td.innerText = `${item['assignment_score']}`;
                    if(!item['assignment_score']) {
                    td.innerText = '0'
                    }
                    tr.appendChild(td);
                })
                container.appendChild(tr);
            })
        } else {
            let row = document.createElement('tr');
            let msg = document.createElement('td');

            msg.innerText = 'Please set an outcome in the Alignments tab';
            row.appendChild(msg);
            container.appendChild(row);
        }
        }
    })
}

const changeHandler = function(e) {
    var elem = e;
    
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
            setTimeout(location.reload(true), 2200);
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
document.getElementById("section").addEventListener("change", changeSection, false);

// Toggle the loader animation
$(document).ajaxStart(function() {
    console.log("started ajax");
    $(".loader-wrap").show();
});

$(document).ajaxStop(function() {
    console.log("stopped ajax");
    $(".loader-wrap").hide();
});