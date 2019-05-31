# Flask related imports
from flask import Flask, request, abort, render_template
from flask_cors import CORS

# Kafka related imports
import json
from kafka import KafkaProducer

# SQLAlchemy related imports
from flask_sqlalchemy import SQLAlchemy

# Default Flask configuration
app = Flask(__name__)

# Enable CORS
CORS(app)

# Configure Flask-SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)


# Kafka producer configuration
# producer = KafkaProducer(bootstrap_servers='localhost:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))

class Dispenser(db.Model):
    """
    A model for dispensers out in the wild. Each dispenser has associated with it
    an ID, a name, a total capacity, and a number of already dispensed items.
    """
    __tablename__ = 'dispensers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    capacity = db.Column(db.Integer)
    dispensed = db.Column(db.Integer)

    def __init__(self, id, name, capacity, dispensed):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.dispensed = dispensed


@app.route('/', methods=['POST', 'GET'])
def index():
    """
    The root endpoint of the gateway system. Dispensers POST to this endpoint, signaling events like STARTUP,
    DISPENSE, and REFILL_REQUEST. Browsers can GET this endpoint for a overview of all the registered dispensers.
    POSTed events to this endpoint are ingested into Kafka, for use by other value adding applications.
    """

    if request.method == 'POST':
        app.logger.info('Event: ' + str(request.get_json()))
        process_event(request.get_json())
        return ''
    else:
        dispensers = Dispenser.query.all()
        return render_template('index.html', dispensers=dispensers)


def permitted(id, token):
    """
    Each dispenser has a hardcoded token. We store mappings from
    the dispenser id to the tokens, and check that these match on each
    request.

    While this does NOT provide a secure way of authenticating dispensers,
    it is a lightweight approach that allows us some level of protection against
    bots and the like.
    """

    # TODO Store these mappings in a database.
    permitted_devices = {1: '42x5yz'}

    return permitted_devices.get(id) == token


def process_event(event):
    """
    Events are first authenticated against a database of id to token mappings.
    If this succeeds, events are dispatched to an appropriate handler, determined
    by the type field.
    """

    # Extract the required parameters from the request body
    id = event.get('id')
    token = event.get('token')
    type = event.get('type')

    # If any of the required parameters are absent, reject the request.
    if (not id) or (not token) or (not type):
        app.logger.warn('Request rejected: Required field absent')
        abort(400)

    # Message type must be on the allowed types
    legal_types = ['STARTUP', 'DISPENSE', 'REFILL', 'REFILLED', 'EMPTY']
    if type not in legal_types:
        app.logger.warn('Request rejected: Invalid event type')
        abort(400)

    # Authenticate the dispenser against our database of tokens.
    if not permitted(event['id'], event['token']):
        app.logger.warn('Request rejected: Invalid authentication token')
        abort(401)

    # Dispatch event to appropriate handler
    if type == 'STARTUP':
        handle_startup(event)
    elif type == 'DISPENSE':
        handle_dispense(event)
    elif type == 'REFILL':
        handle_refill_request(event)
    elif type == 'REFILLED':
        handle_refilled(event)
    elif type == 'EMPTY':
        handle_empty(event)

    # Send the event to the dispensers Kafka topic
    # TODO Topic for startup, dispense, battery level, refill request
    # producer.send(type, event)


def handle_startup(event):
    app.logger.info('Processing STARTUP event: ' + str(event))

    # Create a new dispenser object to mirror the initial state of the dispenser
    new_dispenser = Dispenser(event['id'], 'Another Dispenser', 20, 0)
    db.session.add(new_dispenser)
    db.session.commit()

    # Retrieve and log all the dispensers for validation purposes
    all_dispensers = db.session.query(Dispenser).all()
    for dispenser in all_dispensers:
        print(f'ID: {dispenser.id} Name: {dispenser.name}')

    return


def handle_dispense(event):
    app.logger.info('Processing DISPENSE event: ' + str(event))
    return


def handle_refill_request(event):
    app.logger.info('Processing REFILL event: ' + str(event))
    pass


def handle_refilled(event):
    app.logger.info('Processing REFILLED event: ' + str(event))


def handle_empty(event):
    app.logger.info('Processing EMPTY event: ' + str(event))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
