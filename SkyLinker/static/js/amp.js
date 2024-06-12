function toggleColumn(colIndex, isChecked) {
    var table = document.getElementById('data-table');
    for (var i = 0; i < table.rows.length; i++) {
        var row = table.rows[i];
        if (row.cells[colIndex]) {
            row.cells[colIndex].style.display = isChecked ? '' : 'none';
        }
    }
}

document.querySelectorAll('.sort-toggle').forEach(function(toggle) {
    toggle.addEventListener('click', function(event) {
        event.preventDefault();

        const column = this.getAttribute('data-column');
        const currentUrl = new URL(window.location);
        const currentSort = currentUrl.searchParams.get('sort');
        const currentSortDir = currentUrl.searchParams.get('dir');

        // Determine the new sort direction
        const newSortDir = (currentSort === column && currentSortDir === 'desc') ? 'asc' : 'desc';

        // Update the URL search parameters
        currentUrl.searchParams.set('sort', column);
        currentUrl.searchParams.set('dir', newSortDir);

        // Redirect to the new URL
        window.location.href = currentUrl.toString();
    });
});