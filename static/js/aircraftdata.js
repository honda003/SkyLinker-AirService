$(document).ready(function() {
    $('#id_num_engs').change(function() {
        var numEngines = $(this).val();
        var ENG_SN = $('#Engine-Serial-Number');
        ENG_SN.empty();

        for (var i = 1; i <= numEngines; i++) {
            var headerDiv = $('<h3 class="engine-details-header">Engine ' + i + ' Details <i class="fas fa-angle-down toggle-icon" style="cursor:pointer;"></i></h3>');
            var detailsDiv = $('<div class="engine-details" id="engine-details-' + i + '" style="display: none;"></div>');

            var snDiv = $('<div class="form-group"></div>');
            var fhDiv = $('<div class="form-group"></div>');
            var fcDiv = $('<div class="form-group"></div>');


            // Define default values
            var defaultSN = '00000' + i;
            var defaultFH = '40000:00';
            var defaultFC = 18000;  // Example default value


            var engineSNInput = $('<input type="text" class="form-control" name="eng_sn_' + i + '" placeholder="Serial Number" required>').val(defaultSN);
            var engineFHInput = $('<input type="text" class="form-control" name="eng_fh_' + i + '" placeholder="Flight Hours" required>').val(defaultFH);
            var engineFCInput = $('<input type="number" class="form-control" name="eng_fc_' + i + '" placeholder="Flight Cycles" required>').val(defaultFC);

            snDiv.append('<label for="eng_sn_' + i + '">Engine ' + i + ' Serial Number:</label>').append(engineSNInput);
            fhDiv.append('<label for="eng_fh_' + i + '">Engine ' + i + ' Flight Hours:</label>').append(engineFHInput);
            fcDiv.append('<label for="eng_fc_' + i + '">Engine ' + i + ' Flight Cycles:</label>').append(engineFCInput);

            detailsDiv.append(snDiv, fhDiv, fcDiv);
            headerDiv.find('.toggle-icon').on('click', function() {
                $(this).toggleClass('fa-angle-down fa-angle-up');
                $(this).closest('.engine-details-header').next('.engine-details').toggle();
            });

            ENG_SN.append(headerDiv, detailsDiv);
        }
    });
});