import io
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from barcode import Code128 
from barcode.writer import ImageWriter
import base64
from io import BytesIO
from impedance import preprocessing
import plotly.graph_objs as go
from impedance.models.circuits import CustomCircuit
import matplotlib.pyplot as plt
from impedance.visualization import plot_nyquist

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    meta_params = {'Cell Condition (New or Recycled)':'Recycled', 
                   'Manufacturer':'Molicel', 
                   'Model':'INR21700-P45B',
                   'Type':'Li-ion',
                   'Form Factor':'Cylindrical 21700',
                   'Mass (g)':'70',
                   'Height (mm)': '70.15',
                   'Diameter (mm)': '21.55',
                   'Volume (cm)': '25.59'};
    elect_params = {'Nominal Voltage (V)': '3.6',
                    'Nominal Energy (Wh)': '16.2',
                    'Nominal charge capacity (Ah)': '4.5',
                    'Voltage Range: (V)': '2.5-4.2',
                    'Current (continuous) (A)': '8.61',
                    'Current (peak)(A)': '17.5',
                    'Power (continuous)(W)': 25.6,
                    'Peak (peak)(W)': 50.0,
                    'Energy Density (Gravimetric) (Wh/kg)': 154,
                    'Energy Density (Volumetric) (Wh/l)':375,
                    'Power Density (Gravimetric)(W/kg)':837,
                    'Power Density (Volumetric)(kW/l)':2.04}
    return render_template('index.html', meta_params=meta_params,elect_params=elect_params)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'cell_image' not in request.files or 'cell_data' not in request.files:
        print(request.files)
        return "No files"


    image_file = request.files['cell_image']
    csv_file = request.files['cell_data']

    if image_file.filename == '' or csv_file.filename == '':
        # return redirect(request.url)
        return "Invalid file format"


    if image_file and allowed_file(image_file.filename) and csv_file and allowed_file(csv_file.filename):
        image = image_file.read()
        plot, params = impendence(csv_file)
        # plot = 'impendence(csv_file)'
        # Generate a unique ID for the cell
        cell_id = generate_cell_id()
     
        # Generate a barcode for the cell
        barcode_buffer = BytesIO()

        barcode = Code128(cell_id, writer=ImageWriter()).write(barcode_buffer)
        barcode_bytes = barcode_buffer.getvalue()
        encoded_barcode = base64.b64encode(barcode_bytes).decode('utf-8')
        # encoded_barcode ='sd'
        image = base64.b64encode(image).decode('utf-8')
        # print(barcode)
        # Redirect to a success page or do something else
        return render_template('results.html', barcode=encoded_barcode, cell_id=cell_id, image=image, plot=plot, params=params)
        


    else:
        return "Invalid file format3"

def generate_cell_id():
    unique_id = uuid.uuid4().hex
    numeric_id = ''.join(c for c in unique_id if c.isdigit())
    cell_id = numeric_id[:10]
    return cell_id


def impendence(csv_file):
    frequencies, Z = preprocessing.readCSV(csv_file)
    frequencies, Z = preprocessing.ignoreBelowX(frequencies, Z)
    circuit = 'R0-p(R1,CPE0)-p(R2-W0,CPE1)'
    initial_guess = [.01, .01, 100, .01, .05, 100, 1,1]

    circuit = CustomCircuit(circuit, initial_guess=initial_guess)
    circuit.fit(frequencies, Z)
    # plot =  circuit.plot(frequencies, Z)

    Z_fit = circuit.predict(frequencies)
    # print(Z_fit)
    fig, ax = plt.subplots()
    plot_nyquist(Z, fmt='o', scale=10, ax=ax)
    plot_nyquist(Z_fit, fmt='-', scale=10, ax=ax)

    plt.legend(['Data', 'Fit'])
    params= circuit.parameters_
   # Save the plot as a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Convert the plot to a base64 data string
    plot_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    
    return plot_base64,params

if __name__ == '__main__':
    app.run(debug=True)
