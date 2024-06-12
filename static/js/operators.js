$(document).ready(function() {
    $('#id_num_aircrafts').change(function() {
        var numAircrafts = parseInt($(this).val(), 10);
        var productionDates = $('#production-dates');
        productionDates.empty();

        for (var i = 1; i <= numAircrafts; i++) {
            var detailsHeader = $('<h3 class="aircraft-details-header">Aircraft ' + i + ' Details <i class="fa fa-angle-down toggle-icon" style="cursor:pointer;"></i></h3>');
            var detailsDiv = $('<div class="aircraft-details" id="aircraft-details-' + i + '" style="display: none;"></div>');

            var productionDateInput = $('<input type="date" class="form-control" name="production_date_' + i + '" required>').val('2015-01-01');
            var aircraftTypeInput = $('<input type="text" class="form-control" name="aircraft_type_' + i + '" required>').val('B737-700');
            var aircraftNameInput = $('<input type="text" class="form-control" name="aircraft_name_' + i + '" required>').val('SU-AAA');
            var serialNumberInput = $('<input type="text" class="form-control" name="ac_sn_' + i + '" required>').val("0000" + i);
            var lineNumberInput = $('<input type="text" class="form-control" name="ac_ln_' + i + '" required>').val("000" + i);
            var blockNumberInput = $('<input type="text" class="form-control" name="ac_bn_' + i + '" required>').val("XY00" + i);

            detailsDiv.append(
                $('<div class="form-group"><label>Aircraft ' + i + ' Production Date:</label></div>').append(productionDateInput),
                $('<div class="form-group"><label>Aircraft ' + i + ' Type:</label></div>').append(aircraftTypeInput),
                $('<div class="form-group"><label>Aircraft ' + i + ' Name:</label></div>').append(aircraftNameInput),
                $('<div class="form-group"><label>Aircraft ' + i + ' Serial Number:</label></div>').append(serialNumberInput),
                $('<div class="form-group"><label>Aircraft ' + i + ' Line Number:</label></div>').append(lineNumberInput),
                $('<div class="form-group"><label>Aircraft ' + i + ' Block Number:</label></div>').append(blockNumberInput)
            );

            detailsHeader.find('.toggle-icon').on('click', function() {
                $(this).toggleClass('fa-angle-down fa-angle-up');
                $(this).parent().next('.aircraft-details').toggle();
            });

            productionDates.append(detailsHeader, detailsDiv);
        }
    });
});