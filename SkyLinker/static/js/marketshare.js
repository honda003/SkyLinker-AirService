document.addEventListener('DOMContentLoaded', function () {
    const radios = document.querySelectorAll('input[name="has_historical_data"]');
    const hint = document.getElementById('hint');

    radios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'no') {
                hint.style.display = 'block';
            } else {
                hint.style.display = 'none';
            }
        });
    });
});


function toggleVisibility(id) {
    var element = document.getElementById(id);
    element.style.display = (element.style.display === 'none') ? 'block' : 'none';
}


function toggleTable(tableId) {
console.log("Toggling table: ", tableId); // Debugging line
// Hide all sections first
document.querySelectorAll('.hidden').forEach(div => {
    div.style.display = 'none';
});


// Attempt to find the table
var table = document.getElementById(tableId);
if (table) {
    // If found, display the table
    table.style.display = 'block';
    // Hide any 'no-tasks' messages within this table
    var noTasksMessage = table.querySelector('.no-tasks');
    if (noTasksMessage) {
        noTasksMessage.style.display = 'none';
    }
} else {
    // If the table doesn't exist, handle it by displaying all 'no-tasks' messages
    document.querySelectorAll('.no-tasks').forEach(msg => {
        msg.style.display = 'block';
    });
}
}



function showSelectedMarketChart() {
// Get the selected value from the dropdown
var selectedMarket = document.getElementById('marketSelector').value;

// Hide all charts
var charts = document.getElementsByClassName('charts-container');
for (var i = 0; i < charts.length; i++) {
    charts[i].style.display = 'none';
}

// Show the selected charty
if (selectedMarket) {
    document.getElementById(selectedMarket).style.display = 'block';
}
}

