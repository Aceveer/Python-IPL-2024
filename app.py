import os
from flask import Flask, jsonify, request
import pandas as pd
from flask_cors import CORS
import math

app = Flask(__name__)
CORS(app)  # This will allow all origins by default

# Load CSV files into memory
match_history = pd.read_csv('ipl_2024_matches.csv')
ball_by_ball = pd.read_csv('ipl_2024_deliveries.csv')


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


@app.route('/get-scorecard/<match_no>', methods=['GET'])
def getScorecardFromMatchNo(match_no):
    data= ball_by_ball[['match_no', 'date','venue', 'batting_team','bowling_team', 'innings', 'over', 'striker', 'non_striker', 'bowler', 'runs_of_bat', 'extras', 'wide', 'legbyes', 'byes', 'noballs', 'wicket_type', 'player_dismissed', 'fielder']]
    match = match_history[ ['match_no', 'team1', 'team2', 'innings1_score','innings2_score', 'innings1_wickets','innings2_wickets']]

    #Convert parameter from URL to integer
    match_no = int(match_no)

    #Get match detail from data
    match_data = data[data['match_no'] == match_no]
    general_match_info = match[match['match_no'] == match_no].iloc[0]


    innings_data = {1: {"batting":{}, "bowling": {}, "extras" : {"total":0, "wides" : 0, "no_balls":0,"leg_byes":0,"byes":0}}, 2: {"batting":{}, "bowling":{}, "extras" : {"total":0, "wides" : 0, "no_balls":0,"leg_byes":0,"byes":0}}}

    for _,ball in match_data.iterrows():
        innings = ball['innings']
        batting_team = ball['batting_team']
        bowling_team = ball['bowling_team']
        striker = ball['striker']
        non_striker = ball['non_striker']
        bowler = ball['bowler']
        fielder = ball['fielder']
        player_dismissed = ball['player_dismissed']
        wicket_type = ball['wicket_type']
        runs_of_bat = ball['runs_of_bat']
        extras = ball['extras']
        wides = ball['wide']
        no_balls = ball['noballs']
        leg_byes = ball['legbyes']
        byes = ball['byes']
        over = ball['over']

        if striker not in innings_data[innings]["batting"]:
            innings_data[innings]["batting"][striker] = {
                "batter": striker,
                "runs": 0,
                "balls": 0,
                "fours": 0,
                "sixes": 0,
                "dots": 0,
                "wicket_type": None,
                "fielder": None,
            }
        
        innings_data[innings]["batting"][striker]["runs"] += runs_of_bat
        if no_balls != 1 and wides != 1:
            innings_data[innings]["batting"][striker]["balls"] +=1

        if runs_of_bat == 0:
            innings_data[innings]["batting"][striker]["dots"] +=1
        if runs_of_bat == 4:
            innings_data[innings]["batting"][striker]["fours"] +=1
        if runs_of_bat == 6:
            innings_data[innings]["batting"][striker]["sixes"] +=1
        
        if not pd.isna(player_dismissed):
            innings_data[innings]["batting"][player_dismissed]["wicket_type"] = (
                wicket_type if not (isinstance(wicket_type, float) and math.isnan(wicket_type)) else "not out"
            )
            innings_data[innings]["batting"][player_dismissed]["fielder"] = (
                fielder if not (isinstance(fielder, float) and math.isnan(fielder)) else ""
            )
            innings_data[innings]["batting"][player_dismissed]["bowler"] = (
                bowler if not (isinstance(bowler, float) and math.isnan(bowler)) else ""
            )

        #Bowling Stats
        if bowler not in innings_data[innings]["bowling"]:
            innings_data[innings]["bowling"][bowler] = {
                "bowler": bowler,
                "runs": 0,
                "overs": 0.0,
                "maidens": 0,
                "fours": 0,
                "sixes": 0,
                "wides": 0,
                "no_balls": 0,
                "dots" : 0,
                "wickets" : 0,
            }

        innings_data[innings]["bowling"][bowler]["runs"] += runs_of_bat + extras - (leg_byes + byes)
        innings_data[innings]["bowling"][bowler]["wides"] += wides
        innings_data[innings]["bowling"][bowler]["no_balls"] += no_balls

        if runs_of_bat == 0 and extras == 0:
            innings_data[innings]["bowling"][bowler]["dots"] += 1
        if runs_of_bat == 4:
            innings_data[innings]["bowling"][bowler]["fours"] += 1
        if runs_of_bat == 6:
            innings_data[innings]["bowling"][bowler]["sixes"] += 1
        
        # Calculate inning extras
        innings_data[innings]["extras"]["total"] += extras
        if wides == 1:
            innings_data[innings]["extras"]["wides"] += extras

        innings_data[innings]["extras"]["no_balls"] += no_balls

        if leg_byes == 1:
            innings_data[innings]["extras"]["leg_byes"] += extras - no_balls

        if byes == 1:    
            innings_data[innings]["extras"]["byes"] += extras - no_balls


        # Calculate overs bowled
        if no_balls != 1 and wides != 1:
            current_overs = innings_data[innings]["bowling"][bowler]["overs"]
            balls_bowled = math.floor(current_overs) * 6 + (current_overs - math.floor(current_overs)) * 10
            balls_bowled += 1
            innings_data[innings]["bowling"][bowler]["overs"] = math.floor(balls_bowled / 6) + (balls_bowled % 6) / 10
        
        # Get Wickets
        if wicket_type == "caught" or wicket_type == "bowled":
            innings_data[innings]["bowling"][bowler]["wickets"] += 1

     # Convert to list for JSON response
    response = {
        "innings1": {
            "batting": list(innings_data[1]["batting"].values()),
            "bowling": list(innings_data[1]["bowling"].values()),
            "score" : general_match_info["innings1_score"],
            "wickets" : general_match_info["innings1_wickets"],
            "team" : general_match_info["team1"],
            "extras" : innings_data[1]["extras"]
        },
        "innings2": {
            "batting": list(innings_data[2]["batting"].values()),
            "bowling": list(innings_data[2]["bowling"].values()),
            "score" : general_match_info["innings2_score"],
            "wickets" : general_match_info["innings2_wickets"],
            "team" : general_match_info["team2"],
            "extras" : innings_data[2]["extras"]
        },
    }
    return jsonify(response)

@app.route('/get-fow/<match_no>', methods=['GET'])
def getFallOfWicketsFromMatchNo(match_no):
    data = ball_by_ball[['match_no', 'batting_team', 'bowling_team', 'innings', 'over', 'runs_of_bat', 'extras', 'player_dismissed']]

    # Convert parameter from URL to integer
    match_no = int(match_no)

    # Get match detail from data
    match_data = data[data['match_no'] == match_no]

    ball_by_ball_runs = {1: [], 2: []}
    fall_of_wickets = {1: [], 2: []}
    total_runs = {1: 0, 2: 0}  # Running total for each innings per ball
    run_per_over = {1: {}, 2: {}}  # To track runs per over (0.1 -> 1, 1.1 -> 2...)
    team = {1: {"batting_team": None, "bowling_team": None}, 2: {"batting_team": None, "bowling_team": None}}

    for _, ball in match_data.iterrows():
        over = ball["over"]
        innings = ball["innings"]
        runs_of_bat = ball['runs_of_bat']
        extras = ball['extras']
        player_dismissed = ball['player_dismissed']
        batting_team = ball["batting_team"]
        bowling_team = ball["bowling_team"]

        if team[innings]["batting_team"] is None:  # Only assign if not already set
            team[innings]["batting_team"] = batting_team
        if team[innings]["bowling_team"] is None:  # Only assign if not already set
            team[innings]["bowling_team"] = bowling_team

        # Calculate the ball number (e.g., 0.1 -> 1, 1.1 -> 7, etc.)
        ball_number = int(over) * 6 + int(str(over).split('.')[1])  # ball_number starts from 1, 2, 3...

        # Cumulative runs calculation for each ball
        total_runs[innings] += (runs_of_bat + extras)

        # Update ball-by-ball runs (cumulative runs at each ball)
        found = False
        for idx, ball_data in enumerate(ball_by_ball_runs[innings]):
            if ball_data['ball'] == ball_number:
                ball_by_ball_runs[innings][idx] = {
                    "ball": ball_number,
                    "runs": total_runs[innings]
                }
                found = True
                break
        
        # If no existing ball number found, append new ball data
        if not found:
            ball_by_ball_runs[innings].append({
                "ball": ball_number,
                "runs": total_runs[innings]
            })

        # Capture fall of wickets (player dismissal)
        if isinstance(player_dismissed, str):  # If player was dismissed
            fall_of_wickets[innings].append({
                "ball": ball_number,
                "runs_at_wicket_fall": total_runs[innings],
                "player_dismissed": player_dismissed
            })

        # Track runs per over (for creating run per over stats)
        over_key = int(str(over).split(".")[0])  # Extract the over number (e.g., 0.1 -> 0, 1.1 -> 1)
        if over_key not in run_per_over[innings]:
            run_per_over[innings][over_key] = 0
        
        run_per_over[innings][over_key] += runs_of_bat + extras

    # Create the response structure
    response = {
        "runs": {
            "innings1": ball_by_ball_runs[1],
            "innings2": ball_by_ball_runs[2]
        },
        "FallOfWickets": {
            "innings1": fall_of_wickets[1],
            "innings2": fall_of_wickets[2]
        },
        "runPerOver": {
            "innings1": [{"over": f"{k+1}", "runs": v} for k, v in sorted(run_per_over[1].items())],
            "innings2": [{"over": f"{k+1}", "runs": v} for k, v in sorted(run_per_over[2].items())]
        },
         "teams": {
            "innings1": [{"batting": team[1]["batting_team"], "bowling": team[1]["bowling_team"]}],
            "innings2": [{"batting": team[2]["batting_team"], "bowling": team[2]["bowling_team"]}],
        }
    }

    return jsonify(response)





if __name__ == '__main__':
    # Get the port from the environment variable, default to 5000 if not set
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
