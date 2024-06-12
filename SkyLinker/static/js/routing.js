// Function to toggle the specified FPD field visibility
function toggleSpecifiedFPD() {
    var useMaxFPDCheckbox = document.getElementById('id_use_max_fpd');
    var specifiedFPDField = document.getElementById('id_specified_fpd');
    var specifiedFPDLabel = document.querySelector('label[for="id_specified_fpd"]');

    // Check if the elements exist before trying to change their styles
    if (specifiedFPDField && specifiedFPDLabel && useMaxFPDCheckbox) {
        specifiedFPDField.style.display = useMaxFPDCheckbox.checked ? 'none' : 'inline-block';
        specifiedFPDLabel.style.display = useMaxFPDCheckbox.checked ? 'none' : 'inline-block';

        if (useMaxFPDCheckbox.checked) {
            specifiedFPDField.value = '';
        }
    }
}

// Function to restore the state of the checkbox and the specified FPD field visibility
function restoreCheckboxState() {
    var useMaxFPDCheckbox = document.getElementById('id_use_max_fpd');

    if (useMaxFPDCheckbox) {
        var storedState = localStorage.getItem('useMaxFPDChecked');

        // Only set the checkbox state if a stored state exists
        if (storedState !== null) {
            var isChecked = storedState === 'true';
            useMaxFPDCheckbox.checked = isChecked;
        }

        toggleSpecifiedFPD();
    }
}


// Add event listeners safely
document.addEventListener('DOMContentLoaded', function() {
    restoreCheckboxState();
    var useMaxFPDCheckbox = document.getElementById('id_use_max_fpd');
    if (useMaxFPDCheckbox) {
        useMaxFPDCheckbox.addEventListener('change', function() {
            localStorage.setItem('useMaxFPDChecked', this.checked);
            toggleSpecifiedFPD();
        });
    }
});


// Check box functions ends

// Function bthandle el error
document.addEventListener('DOMContentLoaded', function() {
    // Select all input elements within the form with class 'fpd'
    var inputs = document.querySelectorAll('.fpd input');

    inputs.forEach(function(input) {
        // Add an event listener to each input field for input changes
        input.addEventListener('input', function() {
            // Select all <li> elements inside the .fpd_errors container
            var errorMessages = document.querySelectorAll('.fpd_errors li');

            // Loop through all error messages and hide them
            errorMessages.forEach(function(errorMessage) {
                errorMessage.style.display = 'none';
            });
        });
    });
});


