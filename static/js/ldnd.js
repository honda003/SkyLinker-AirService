function toggleColumns(colIndexes, isChecked) {
    var table = document.getElementById('data-table');
    for (var i = 0; i < table.rows.length; i++) {
        var row = table.rows[i];
        colIndexes.forEach(function (colIndex) {
            if (row.cells[colIndex]) {
                row.cells[colIndex].style.display = isChecked ? '' : 'none';
            }
        });
    }
}

document.getElementById('sort-toggle').addEventListener('click', function(event) {
    event.preventDefault();

    const currentUrl = new URL(window.location);
    const currentSortOrder = currentUrl.searchParams.get('order');

    // Toggle sort order between 'asc' and 'desc'
    const newSortOrder = currentSortOrder === 'desc' ? 'asc' : 'desc';

    // Set the new sort order in the URL query parameters
    currentUrl.searchParams.set('sort', 'excel_data__MPD_ITEM_NUMBER');
    currentUrl.searchParams.set('order', newSortOrder);

    // Redirect to the new URL
    window.location.href = currentUrl.toString();
});


// function toggleSticker() {
//     var sticker = document.getElementById('sideSticker');
//     var button = document.querySelector('.toggle-button');
    
//     if (sticker.classList.contains('active')) {
//         sticker.classList.remove('active');
//         sticker.style.left = '-250px'; // Slide out
//         button.style.left = '-55px'; // Button goes back to the left edge
//     } else {
//         sticker.classList.add('active');
//         sticker.style.left = '0px'; // Slide in
//         button.style.left = '195px'; // Button moves right with the sticker
//     }
// }

//Before responsivness

// function toggleSticker() {
//     var sticker = document.getElementById('sideSticker');
//     var button = document.querySelector('.toggle-button');
    
//     if (sticker.classList.contains('active')) {
//         sticker.classList.remove('active');
//         sticker.style.left = '-250px'; // Slide out
//         button.style.position = 'absolute'; // Keep the button in the flow of the document
//         button.style.left = '50px'; // Align with the container or screen edge
//     } else {
//         sticker.classList.add('active');
//         sticker.style.left = '0px'; // Slide in
//         button.style.position = 'fixed'; // Fix the button to the viewport
//         button.style.left = '250px'; // Align with the sidebar
//     }
// }

// function toggleSticker() {
//     var sticker = document.getElementById('sideSticker');
//     var button = document.querySelector('.toggle-button');
    
//     // Toggle the active class to open or close the sticker
//     sticker.classList.toggle('active');

//     updatePositions(); // Call the function to update positions of sticker and button
// }

// function updatePositions() {
//     var sticker = document.getElementById('sideSticker');
//     var button = document.querySelector('.toggle-button');
//     var windowWidth = window.innerWidth; // Get the current window width

//     if (sticker.classList.contains('active')) {
//         sticker.style.left = '0'; // Slide in

//         // Fix the button to the viewport and adjust its position
//         button.style.position = 'fixed'; 
//         if (windowWidth <= 768) {
//             button.style.left = '250px'; // Move button to the end of the viewport on smaller screens
//         } else {
//             button.style.left = '250px'; // Align with the sidebar on larger screens
//         }
//     } else {
//         sticker.style.left = '-250px'; // Slide out

//         // Keep the button in the flow of the document and adjust its position
//         button.style.position = 'absolute'; 
//         if (windowWidth <= 768) {
//             button.style.left = '10px'; // Keep button closer to the edge on smaller screens
//         } else {
//             button.style.left = '50px'; // Align with the container or screen edge on larger screens
//         }
//     }
// }

// // Add an event listener to handle screen resizing
// window.addEventListener('resize', updatePositions);

// // Initial adjustment to ensure the correct position on page load
// updatePositions();

function toggleSticker() {
    var sticker = document.getElementById('sideSticker');
    sticker.classList.toggle('active'); // This toggles the active class, showing or hiding the sticker
}

function closeSticker() {
    var sticker = document.getElementById('sideSticker');
    sticker.classList.remove('active'); // This will ensure the sticker is hidden
}

// Update positions function is not required anymore since the button does not move

