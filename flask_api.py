from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory database simulation
items = []

@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(items)

@app.route('/items', methods=['POST'])
def create_item():
    item = request.get_json()
    items.append(item)
    return jsonify(item), 201

@app.route('/items/<int:index>', methods=['GET'])
def get_item(index):
    if index < len(items):
        return jsonify(items[index])
    else:
        return jsonify({'error': 'Item not found'}), 404

@app.route('/items/<int:index>', methods=['PUT'])
def update_item(index):
    if index < len(items):
        item = request.get_json()
        items[index] = item
        return jsonify(item)
    else:
        return jsonify({'error': 'Item not found'}), 404

@app.route('/items/<int:index>', methods=['DELETE'])
def delete_item(index):
    if index < len(items):
        del items[index]
        return jsonify({'message': 'Item deleted'})
    else:
        return jsonify({'error': 'Item not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
