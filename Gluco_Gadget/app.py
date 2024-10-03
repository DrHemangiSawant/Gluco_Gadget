from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import plotly.graph_objs as go
import plotly.offline as pyo
import os
import pandas as pd

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the data model
class BloodSugar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    pre_prandial_time = db.Column(db.String(5), nullable=False)
    post_prandial_time = db.Column(db.String(5), nullable=False)
    pre_prandial = db.Column(db.Float, nullable=False)
    post_prandial = db.Column(db.Float, nullable=False)

# Create the database if it doesn't exist
if not os.path.exists('data.db'):
    with app.app_context():
        db.create_all()

def render_template_with_graph(template_name):
    # Retrieve data from the database, limiting to the latest 7 dates
    data = BloodSugar.query.order_by(BloodSugar.date.desc()).limit(8).all()

    df = pd.DataFrame([{
        'date': d.date,
        'pre_prandial_time': d.pre_prandial_time,
        'post_prandial_time': d.post_prandial_time,
        'pre_prandial': d.pre_prandial,
        'post_prandial': d.post_prandial
    } for d in data])

    if not df.empty:
        df['pre_prandial_datetime'] = pd.to_datetime(df['date'] + ' ' + df['pre_prandial_time'])
        df['post_prandial_datetime'] = pd.to_datetime(df['date'] + ' ' + df['post_prandial_time'])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['pre_prandial_datetime'], y=df['pre_prandial'], mode='lines+markers', name='Pre-Prandial'))
        fig.add_trace(go.Scatter(x=df['post_prandial_datetime'], y=df['post_prandial'], mode='lines+markers', name='Post-Prandial'))

        fig.update_layout(
            xaxis_title='Date and Time',
            yaxis_title='Blood Sugar Level',
            xaxis=dict(
                tickformat='%Y-%m-%d',
            )
        )

        graph_html = pyo.plot(fig, output_type='div', include_plotlyjs=False)
    else:
        graph_html = "<p>No data available.</p>"

    return render_template(template_name, graph_html=graph_html)


@app.route('/')
def index():
    return render_template_with_graph('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    date = request.form['date']
    pre_prandial_time = request.form['pre_prandial_time']
    post_prandial_time = request.form['post_prandial_time']
    pre_prandial = float(request.form['pre_prandial'])
    post_prandial = float(request.form['post_prandial'])

    new_entry = BloodSugar(
        date=date,
        pre_prandial_time=pre_prandial_time,
        post_prandial_time=post_prandial_time,
        pre_prandial=pre_prandial,
        post_prandial=post_prandial
    )

    db.session.add(new_entry)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/filter')
def filter_page():
    return render_template_with_graph('filter.html')

@app.route('/update_graph', methods=['POST'])
def update_graph():
    min_pre_prandial = request.form.get('min_pre_prandial')
    max_pre_prandial = request.form.get('max_pre_prandial')
    min_post_prandial = request.form.get('min_post_prandial')
    max_post_prandial = request.form.get('max_post_prandial')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    specific_date = request.form.get('specific_date')

    query = BloodSugar.query
    if min_pre_prandial:
        query = query.filter(BloodSugar.pre_prandial >= float(min_pre_prandial))
    if max_pre_prandial:
        query = query.filter(BloodSugar.pre_prandial <= float(max_pre_prandial))
    if min_post_prandial:
        query = query.filter(BloodSugar.post_prandial >= float(min_post_prandial))
    if max_post_prandial:
        query = query.filter(BloodSugar.post_prandial <= float(max_post_prandial))
    if start_date:
        query = query.filter(BloodSugar.date >= start_date)
    if end_date:
        query = query.filter(BloodSugar.date <= end_date)
    if specific_date:
        query = query.filter(BloodSugar.date == specific_date)

    data = query.all()
    
    df = pd.DataFrame([{
        'date': d.date,
        'pre_prandial_time': d.pre_prandial_time,
        'post_prandial_time': d.post_prandial_time,
        'pre_prandial': d.pre_prandial,
        'post_prandial': d.post_prandial
    } for d in data])
    
    if not df.empty:
        df['pre_prandial_datetime'] = pd.to_datetime(df['date'] + ' ' + df['pre_prandial_time'])
        df['post_prandial_datetime'] = pd.to_datetime(df['date'] + ' ' + df['post_prandial_time'])

        fig = go.Figure()

        if specific_date:
            # Pre-prandial color logic
            if 70 <= df['pre_prandial'].values[0] <= 100:
                pre_color = 'green'
            else:
                pre_color = 'red'

            # Post-prandial color logic
            if 100 <= df['post_prandial'].values[0] <= 140:
                post_color = 'green'
            else:
                post_color = 'red'
            
            fig.add_trace(go.Bar(x=['Pre-Prandial'], y=[df['pre_prandial'].values[0]], name='Pre-Prandial', marker=dict(color=pre_color)))
            fig.add_trace(go.Bar(x=['Post-Prandial'], y=[df['post_prandial'].values[0]], name='Post-Prandial', marker=dict(color=post_color)))
        else:
            fig.add_trace(go.Scatter(x=df['pre_prandial_datetime'], y=df['pre_prandial'], mode='lines+markers', name='Pre-Prandial'))
            fig.add_trace(go.Scatter(x=df['post_prandial_datetime'], y=df['post_prandial'], mode='lines+markers', name='Post-Prandial'))

        fig.update_layout(
            xaxis_title='Date and Time' if not specific_date else 'Measurement',
            yaxis_title='Blood Sugar Level',
            xaxis=dict(
                tickformat='%Y-%m-%d',
            )
        )

        graph_html = pyo.plot(fig, output_type='div', include_plotlyjs=False)
    else:
        graph_html = "<p>No data available for the selected filters.</p>"

    return jsonify({'graph_html': graph_html})


if __name__ == '__main__':
    app.run(debug=True)
