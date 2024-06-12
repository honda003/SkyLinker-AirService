import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import AircraftDataForm, EnginesForm
from .models import AircraftData, EngineDetails
from Operator.models import OperatorInput, AircraftDetails
from io import StringIO
from django.db import transaction


@login_required
def aircraft_data_view(request):
    form_submitted = False
    eng_fh_errors = []  # Error list for engine flight hours

    if request.method == 'POST':
        engines_form = EnginesForm(request.POST)
        form = AircraftDataForm(request.POST)
        
        if engines_form.is_valid() and form.is_valid():
            # Retrieve or create an object based on Airline_Name and Aircraft_Name
            
            airline = form.cleaned_data['Airline_Name']
            aircraft = form.cleaned_data['Aircraft_Name']
            current_date = form.cleaned_data['current_date']
            current_flight_hours =form.cleaned_data['current_flight_hours'] 
            current_flight_cycles= form.cleaned_data['current_flight_cycles']
            apu_hours_to_flight_hours_ratio = form.cleaned_data['apu_hours_to_flight_hours_ratio']
            apu_sn = form.cleaned_data['apu_sn']
            apu_fh = form.cleaned_data['apu_fh']
            apu_fc = form.cleaned_data['apu_fc']
            
            # Convert current_date to a string in the format YYYY-MM-DD if it's not None
            formatted_date = current_date.strftime('%Y-%m-%d') if current_date else 'No Date'
            
             # Fetch actual names or attributes from the model instances
            airline_name = airline.Airline_Name if airline else "Unknown Airline"  # Ensure 'name' is the correct field
            aircraft_name = aircraft.aircraft_name if aircraft else "Unknown Aircraft"  # Ensure 'name' is the correct field

            
            print(f'airline: {airline}')
            print(f'aircraft: {aircraft}')
            
            # Aircraft DataFrame
            # Aircraft DataFrame
            aircraft_data = {
                'Airline Name': [airline_name],
                'Aircraft Name': [aircraft_name],
                'Current Date': [formatted_date],
                'Current Flight Hours': [current_flight_hours],
                'Current Flight Cycles': [current_flight_cycles]
            }
            aircraft_df = pd.DataFrame(aircraft_data)

            # APU DataFrame
            apu_data = {
                'APU Serial Number': [apu_sn],
                'APU Flight Hours': [apu_fh],
                'APU Flight Cycles': [apu_fc],
                'APU To Aircraft Flight Hours Ratio': [apu_hours_to_flight_hours_ratio]
            }
            apu_df = pd.DataFrame(apu_data)


            print(aircraft_df)
            print(apu_df)
            
            aircraft_df_json = aircraft_df.to_json(orient='split')
            request.session['aircraft_df'] = aircraft_df_json
            
            apu_df_json = apu_df.to_json(orient='split')
            request.session['apu_df'] = apu_df_json
            
            AircraftData.objects.filter(Aircraft_Name=aircraft).delete() # to delete the old aircraft data if re-submitted
            aircraft_input, created = AircraftData.objects.get_or_create(
                Airline_Name=airline,
                Aircraft_Name=aircraft,
                current_date = current_date,
                current_flight_cycles = current_flight_cycles,
                current_flight_hours = current_flight_hours,
                apu_hours_to_flight_hours_ratio = apu_hours_to_flight_hours_ratio,
                apu_sn = apu_sn,
                apu_fh = apu_fh,
                apu_fc = apu_fc,
                defaults={'num_engs': engines_form.cleaned_data['num_engs']}
            )
            
            
              
            # Update aircraft_input with the number of engines
            aircraft_input.num_engs = engines_form.cleaned_data['num_engs']
            aircraft_input.save()

            # Delete old engine details for this aircraft
            EngineDetails.objects.filter(Aircraft_Name=aircraft_input).delete()
            
            valid_engines = True
            eng_data_list = []  # Initialize an empty DataFrame
            for i in range(1, aircraft_input.num_engs + 1):
                eng_sn = request.POST.get(f'eng_sn_{i}', '')
                eng_fh = request.POST.get(f'eng_fh_{i}', '')
                eng_fc = request.POST.get(f'eng_fc_{i}', '')

                # Validate eng_fh format
                try:
                    hours, minutes = eng_fh.split(':')
                    hours = int(hours)
                    minutes = int(minutes)
                    if not (0 <= minutes < 60):
                        raise ValueError('Minutes must be between 0 and 59.')
                except ValueError as e:
                    eng_fh_errors.append(f"Engine {i}: Error in flight hours format")
                    valid_engines = False
                    continue

                if eng_sn and eng_fh and eng_fc:
                    EngineDetails.objects.create(
                        Aircraft_Name=aircraft_input,
                        Airline_Name=aircraft_input.Airline_Name,
                        eng_sn=eng_sn,
                        eng_fh=eng_fh,
                        eng_fc=eng_fc,
                    )
                    
                    eng_data_list.append({
                        'Serial Number': eng_sn,
                        'Flight Hours': eng_fh,
                        'Flight Cycles': eng_fc
                    })

                    # Create DataFrame from the list
                    eng_df = pd.DataFrame(eng_data_list)
                    
                    eng_df_json = eng_df.to_json(orient='split')
                    request.session['eng_df'] = eng_df_json

            form_submitted = valid_engines and not eng_fh_errors
            
            return redirect('view_data')

    else:
        engines_form = EnginesForm()
        form = AircraftDataForm()

    return render(request, 'pages/aircraftdata.html', {
        'engines_form': engines_form,
        'form': form,
        'form_submitted': form_submitted,
        'eng_fh_errors': eng_fh_errors,
    })

def view_data(request):
    if 'aircraft_df' not in request.session or 'apu_df' not in request.session or 'eng_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('aircraft_data_view')
    else:
        aircraft_df_json = request.session.get('aircraft_df')
        aircraft_df = pd.read_json(StringIO(aircraft_df_json), orient='split')
        
        apu_df_json = request.session.get('apu_df')
        apu_df = pd.read_json(StringIO(apu_df_json), orient='split')

        eng_df_json = request.session.get('eng_df')
        eng_df = pd.read_json(StringIO(eng_df_json), orient='split')
    
        return render(request, 'pages/aircraftdata.html', {
        'form_submitted': True,  # This ensures the form is hidden when viewing data
        'aircraft_df': aircraft_df.to_html(classes=["table", "table-striped"], index=False),
        'apu_df': apu_df.to_html(classes=["table", "table-striped"], index=False),
        'eng_df': eng_df.to_html(classes=["table", "table-striped"], index=False),
    })
        
