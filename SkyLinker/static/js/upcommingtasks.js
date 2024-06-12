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
