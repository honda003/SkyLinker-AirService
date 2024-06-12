document.addEventListener("DOMContentLoaded", function() {
    const yesOption = document.querySelector('input[name="has_optional_flights"][value="yes"]');
    const noOption = document.querySelector('input[name="has_optional_flights"][value="no"]');
    const allFlightsOptionalCheckbox = document.querySelector('input[name="all_flights_optional"]');
    const optionalFlightOptionsDiv = document.getElementById('optionalFlightOptions');
    const selectSpecificFlightsDiv = document.getElementById('selectSpecificFlights');

    // Function to control the display based on the checkbox state
    function toggleSpecificFlightsDisplay() {
        if (allFlightsOptionalCheckbox && selectSpecificFlightsDiv) {
            selectSpecificFlightsDiv.style.display = allFlightsOptionalCheckbox.checked ? 'none' : 'block';
        }
    }

    if (yesOption) {
        yesOption.addEventListener('change', function() {
            if (optionalFlightOptionsDiv) {
                optionalFlightOptionsDiv.style.display = 'block';
            }
            toggleSpecificFlightsDisplay(); // Ensure correct display state when switching options
        });
    }

    if (noOption) {
        noOption.addEventListener('change', function() {
            if (optionalFlightOptionsDiv && selectSpecificFlightsDiv) {
                optionalFlightOptionsDiv.style.display = 'none';
                selectSpecificFlightsDiv.style.display = 'none';
                if (allFlightsOptionalCheckbox) {
                    allFlightsOptionalCheckbox.checked = false;
                }
            }
        });
    }

    if (allFlightsOptionalCheckbox) {
        allFlightsOptionalCheckbox.addEventListener('change', toggleSpecificFlightsDisplay);
    }

    // Initial check on page load to ensure correct display
    if (allFlightsOptionalCheckbox && selectSpecificFlightsDiv) {
        toggleSpecificFlightsDisplay();
    }
});


function toggleHelpText(helpId, event) {
    var helpText = document.getElementById(helpId);
    var icon = event.currentTarget; // The element that triggered the event (info icon)

    // Get the bounding rectangle of the icon
    var rect = icon.getBoundingClientRect();

    // Calculate the absolute position on the page
    var iconTop = rect.top + window.scrollY; // Absolute Y position
    var iconLeft = rect.left + window.scrollX; // Absolute X position

    // Position the tooltip 20px below and to the right of the icon
    helpText.style.top = (iconTop - 80) + 'px'; // Below the icon
    helpText.style.left = (iconLeft + 20) + 'px'; // Right of the icon

    // Make tooltip visible
    helpText.style.display = 'block';
    helpText.style.opacity = 0;
    var opacity = 0;
    var intervalID = setInterval(function() {
        if (opacity < 1) {
            opacity += 0.1;
            helpText.style.opacity = opacity;
        } else {
            clearInterval(intervalID);
        }
    }, 10); // Smooth fade-in effect
}

function hideHelpText(helpId) {
    var helpText = document.getElementById(helpId);
    helpText.style.display = 'none'; // Hide help text
}

function toggleFleetDetails(index) {
    var detailsDiv = document.getElementById('fleetDetails' + index);
    var arrowIcon = document.querySelector('.toggle-arrow[data-index="' + index + '"]');

    if (detailsDiv.style.display === 'none') {
        detailsDiv.style.display = 'block';
        arrowIcon.classList.remove('fa-angle-down');
        arrowIcon.classList.add('fa-angle-up');
    } else {
        detailsDiv.style.display = 'none';
        arrowIcon.classList.remove('fa-angle-up');
        arrowIcon.classList.add('fa-angle-down');
    }
}

// function toggleHelpText(helpId) {
//     var helpText = document.getElementById(helpId).innerHTML;
//     var modal = document.getElementById('helpModal');
//     var modalText = document.getElementById('helpText');
//     var span = document.getElementsByClassName("close")[0];

//     modalText.innerHTML = helpText;
//     modal.style.display = "block";

//     span.onclick = function() {
//         modal.style.display = "none";
//     }

//     window.onclick = function(event) {
//         if (event.target === modal) {
//             modal.style.display = "none";
//         }
//     }
// }



