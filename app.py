import os
from flask import Flask, jsonify, request
import pandas as pd
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This will allow all origins by default

# Load CSV files into memory
match_history = pd.read_csv('ipl_2024_matches.csv')
ball_by_ball = pd.read_csv('ipl_2024_deliveries.csv')

@app.route('/api/match-history', methods=['GET'])
def get_match_history():
    # Convert match history data to JSON format
    return jsonify(match_history.to_dict(orient='records'))

@app.route('/points-table', methods=['GET'])
def points_table():

    # Select only the required columns
    selected_columns = match_history[['team1', 'team2', 'winning_team','match_no']]
    # Convert to a list of dictionaries
    result = selected_columns.to_dict(orient='records')

    points_table = {}

    for match in result:
        team1 = match['team1']
        team2 = match['team2']
        winner = match['winning_team']

        points_table[team1] = points_table.get(team1,0)
        points_table[team2] = points_table.get(team2,0)

        if winner != 'TIE' and match['match_no'] <= 70:
            points_table[winner] +=2
        elif winner =='TIE' and match['match_no'] <= 70:
            points_table[team1] +=1
            points_table[team2] +=1

    sorted_points_table = dict(sorted(points_table.items(), key=lambda x: x[1], reverse=True))
    return jsonify(sorted_points_table)

@app.route('/venues', methods=['GET'])
def venues():
    # Select only the required columns
    selected_columns = match_history[['venue']]
    # Convert to a list of dictionaries
    result = selected_columns.to_dict(orient='records')

    venues = []

    for venue in result:
        if venue not in venues:
            venues.append(venue)

    return jsonify(venues)

@app.route('/matches', methods=['GET'])
def matches():
    # Select only the required columns
    match_column = match_history[['match_no','date', 'venue', 'city', 'team1', 'team2', 'toss_winner', 'toss_decision', 'innings1_score', 'innings1_wickets', 'innings2_score', 'innings2_wickets', 'winning_team', 'margin', 'won_by', 'player_of_the_match']]
    delivery_columns = ball_by_ball[['match_no', 'innings', 'over']]
    # Convert to a list of dictionaries
    result_match = match_column.to_dict(orient='records')
    result_delivery = delivery_columns.to_dict(orient='records')

    matches = []
    balls = {}

    for match in result_match:
        if(match["winning_team"] != "TIE"):
            match_item = {
                "match_no" : match['match_no'],
                "date" : match['date'],
                "venue" : match['venue'],
                "city" : match['city'],
                "team1" : match['team1'],
                "team2" : match['team2'],
                "toss_winner" : match['toss_winner'],
                "toss_decision" : match['toss_decision'],
                "innings1_score" : match['innings1_score'],
                "innings1_wickets" : match['innings1_wickets'],
                "innings2_score" : match['innings2_score'],
                "innings2_wickets" : match['innings2_wickets'],
                "winning_team" : match['winning_team'],
                "margin" : match['margin'],
                "won_by" : match['won_by'],
                "player_of_the_match" : match['player_of_the_match']
            }
            matches.append(match_item)

    for ball in result_delivery:
        match_no = ball['match_no']
        innings = ball["innings"]
        over = ball["over"]

        if match_no not in balls:
            balls[match_no] = {"innings1_overs": None, "innings2_overs": None}
        
        if innings == 1:
            if balls[match_no]["innings1_overs"] is None or over > balls[match_no]["innings1_overs"]:
                balls[match_no]["innings1_overs"] = over
        elif innings == 2:
            if balls[match_no]["innings2_overs"] is None or over > balls[match_no]["innings2_overs"]:
                balls[match_no]["innings2_overs"] = over

        for match in matches:
            match_no = match["match_no"]
            if match_no in balls:
                match["innings1_overs"] = balls[match_no]["innings1_overs"]
                match["innings2_overs"] = balls[match_no]["innings2_overs"]


    return jsonify(matches)

@app.route('/players', methods=['GET'])
def players():
    # Select only the required columns
    selected_columns = match_history[['team1', 'team2', 'team1_players', 'team2_players']]
    # Convert to a list of dictionaries
    result = selected_columns.to_dict(orient='records')

    team_players = {}

    for match in result:
        team1 = match["team1"]
        team2 = match["team2"]

        team1_players = match["team1_players"] #Excel Data
        team2_players = match["team2_players"] #Excel Data

        team1_players_list = team1_players.split(", ")  #List of Players On Game Day
        team2_players_list = team2_players.split(", ")  #List Of Players On Game Day

        if team1 != '-' or team2 != '-':
            if team1 not in team_players:
                team_players[team1] = []

            if team2 not in team_players:
                team_players[team2] = []

            for player1 in team1_players_list:
                if player1 not in team_players[team1]:
                    team_players[team1].append(player1)

            for player2 in team2_players_list:
                if player2 not in team_players[team2]:
                    team_players[team2].append(player2)

    
    return jsonify(team_players)

if __name__ == '__main__':
    # Get the port from the environment variable, default to 5000 if not set
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
