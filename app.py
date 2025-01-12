from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)

# Load CSV files into memory
match_history = pd.read_csv('ipl_2024_matches.csv')
ball_by_ball = pd.read_csv('ipl_2024_deliveries.csv')

@app.route('/api/match-history', methods=['GET'])
def get_match_history():
    # Convert match history data to JSON format
    return jsonify(match_history.to_dict(orient='records'))

@app.route('/api/player-analysis', methods=['GET'])
def player_analysis():
    # Get the playerId from query parameters
    player_id = request.args.get('playerId')
    
    # Filter ball-by-ball data for the given player ID
    player_data = ball_by_ball[ball_by_ball['batsman_id'] == int(player_id)]
    
    # Convert the filtered data to JSON format
    return jsonify(player_data.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
