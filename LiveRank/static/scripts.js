document.querySelectorAll('.read-more').forEach((button) => {
    button.addEventListener('click', (event) => {
        const shortSpan = event.target.previousElementSibling.previousElementSibling;
        const fullSpan = event.target.previousElementSibling;
        
        if (fullSpan.style.display === 'none') {
            fullSpan.style.display = 'inline';
            shortSpan.style.display = 'none';
            event.target.textContent = 'Read Less';
        } else {
            fullSpan.style.display = 'none';
            shortSpan.style.display = 'inline';
            event.target.textContent = 'Read More';
        }
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

fetch('/delete_session/' + sessionId + '/', {
    method: 'DELETE',
    headers: {
        'Content-Type': 'application/json',
        // Include the CSRF token in the request header
        'X-CSRFToken': csrftoken
    },
})

function confirmDelete(sessionId) {
    var confirmBox = document.getElementById('confirm-delete-box');
    confirmBox.style.display = "block";

    var yesButton = confirmBox.querySelector('.yes-button');
    yesButton.onclick = function() {
        deleteSession(sessionId);
        confirmBox.style.display = "none";
    };

    var noButton = confirmBox.querySelector('.no-button');
    noButton.onclick = function() {
        confirmBox.style.display = "none";
    };
}

function deleteSession(sessionId) {
    // Call the Django view to delete the session
    fetch('/delete_session/' + sessionId.replace('session-', ''), {method: 'DELETE'})
    .then(function(response) {
        if (response.ok) {
            // Remove the DOM element corresponding to the deleted session
            var sessionElement = document.getElementById(sessionId);
            sessionElement.remove();
        } else {
            console.log('Failed to delete session');
        }
    })
}


function toggleSession(sessionId) {
    var sessionContent = document.getElementById(sessionId);
    var arrow = sessionContent.previousElementSibling.children[0];

    if (sessionContent.style.display === "none") {
        sessionContent.style.display = "block";
        arrow.textContent = "\u2192";  // change arrow to right
    } else {
        sessionContent.style.display = "none";
        arrow.textContent = "\u2193";  // change arrow to down
    }
}