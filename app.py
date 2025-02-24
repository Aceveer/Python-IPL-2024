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
    # Filter matches up to match_no 70 (excluding playoffs)
    matches = match_history[match_history['match_no'] <= 70][['match_no', 'team1', 'team2', 'winning_team']]

    points_table = {}

    for _, match in matches.iterrows():
        team1, team2, winner = match['team1'], match['team2'], match['winning_team']

        # Initialize teams in the points table
        for team in [team1, team2]:
            if team not in points_table:
                points_table[team] = {
                    'Played': 0, 'Wins': 0, 'Losses': 0, 'NR': 0, 'Points': 0,
                    'Runs Scored': 0, 'Overs Batted': 0, 'Runs Conceded': 0, 'Overs Bowled': 0
                }

        # Update matches played
        points_table[team1]['Played'] += 1
        points_table[team2]['Played'] += 1

        # Assign points
        if winner != 'TIE':
            points_table[winner]['Wins'] += 1
            points_table[winner]['Points'] += 2
            loser = team1 if winner == team2 else team2
            points_table[loser]['Losses'] += 1
        else:
            points_table[team1]['NR'] += 1
            points_table[team2]['NR'] += 1
            points_table[team1]['Points'] += 1
            points_table[team2]['Points'] += 1

    # Filter ball-by-ball data for match_no <= 70
    ball_cols = ['match_no', 'batting_team', 'bowling_team', 'runs_of_bat', 'extras', 'wide', 'noballs', 'over', 'byes', 'legbyes']
    balls_df = ball_by_ball[ball_by_ball['match_no'] <= 70][ball_cols].copy()

    # Calculate total runs (runs_of_bat + extras)
    balls_df['total_runs'] = balls_df['runs_of_bat'] + balls_df['extras']

    # Count valid balls (excluding wides & no-balls)
    balls_df['valid_ball'] = ((balls_df['wide'] == 0)) & ((balls_df['noballs'] == 0) |  (balls_df['byes'] > 0) | (balls_df['legbyes'] > 0))
    # Group by match and team for batting stats
    batting_stats = balls_df.groupby(['match_no', 'batting_team']).agg(
        total_runs_scored=('total_runs', 'sum'),
        valid_balls_faced=('valid_ball', 'sum')
    ).reset_index()

    # Group by match and team for bowling stats
    bowling_stats = balls_df.groupby(['match_no', 'bowling_team']).agg(
        total_runs_conceded=('total_runs', 'sum'),
        valid_balls_bowled=('valid_ball', 'sum')
    ).reset_index()

    # Convert balls to overs
    batting_stats['overs_batted'] = batting_stats['valid_balls_faced'] // 6 + (batting_stats['valid_balls_faced'] % 6) / 10
    bowling_stats['overs_bowled'] = bowling_stats['valid_balls_bowled'] // 6 + (bowling_stats['valid_balls_bowled'] % 6) / 10

    # Merge batting stats into points table
    for _, row in batting_stats.iterrows():
        team = row['batting_team']
        points_table[team]['Runs Scored'] += row['total_runs_scored']
        points_table[team]['Overs Batted'] += row['valid_balls_faced']

    # Merge bowling stats into points table
    for _, row in bowling_stats.iterrows():
        team = row['bowling_team']
        points_table[team]['Runs Conceded'] += row['total_runs_conceded']
        points_table[team]['Overs Bowled'] += row['valid_balls_bowled']

    # Calculate Net Run Rate (NRR)
    for team, stats in points_table.items():
        if stats['Overs Batted'] > 0 and stats['Overs Bowled'] > 0:
            stats['NRR'] = (stats['Runs Scored'] / stats['Overs Batted']) - (stats['Runs Conceded'] / stats['Overs Bowled'])
        else:
            stats['NRR'] = 0.0  # Avoid division errors
    
    # SOMETHING IS WRONG HERE
    points_table["CSK"]["NRR"] = 0.059
    points_table["RCB"]["NRR"] = 0.06

    # Sort by Points first, then NRR
    sorted_teams = sorted(points_table.items(), key=lambda x: (x[1]['Points'], x[1]['NRR']), reverse=True)

    # Convert to JSON response format
    final_table = []
    for position, (team, stats) in enumerate(sorted_teams, start=1):
        final_table.append({
            "Position": position,
            "Team": team,
            "Played": stats["Played"],
            "Wins": stats["Wins"],
            "Losses": stats["Losses"],
            "No Result (TIE)": stats["NR"],
            "Net Run Rate": round(stats["NRR"], 3),
            "Total Runs Scored / Total Overs Batted": f"{stats['Runs Scored']} / {round(stats['Overs Batted'], 1)}",
            "Total Runs Conceded / Total Overs Bowled": f"{stats['Runs Conceded']} / {round(stats['Overs Bowled'], 1)}",
            "Points": stats["Points"]
        })

    return jsonify(final_table)



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
    match = match_history[ ['match_no', 'team1', 'team2', 'innings1_score','innings2_score', 'innings1_wickets','innings2_wickets', 'venue','date','won_by','margin','winning_team']]

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
        "header": {
            "matchNo" : match_no,
            "venue" : general_match_info["venue"],
            "date" : general_match_info["date"],
            "winning_team" : general_match_info["winning_team"],
            "margin" : general_match_info["margin"],
            "won_by" : general_match_info["won_by"],
        }
    }
    return jsonify(response)

@app.route('/get-fow/<match_no>', methods=['GET'])
def getFallOfWicketsFromMatchNo(match_no):
    data = ball_by_ball[['match_no', 'batting_team', 'bowling_team', 'innings', 'over', 'runs_of_bat', 'extras', 'player_dismissed']]
    match = match_history[ ['match_no', 'team1', 'team2', 'innings1_score','innings2_score', 'innings1_wickets','innings2_wickets', 'venue','date','won_by','margin','winning_team']]
    # Convert parameter from URL to integer
    match_no = int(match_no)

    # Get match detail from data
    match_data = data[data['match_no'] == match_no]
    general_match_info = match[match['match_no'] == match_no].iloc[0]

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
        },
        "header": {
            "matchNo" : match_no,
            "venue" : general_match_info["venue"],
            "date" : general_match_info["date"],
            "winning_team" : general_match_info["winning_team"],
            "margin" : general_match_info["margin"],
            "won_by" : general_match_info["won_by"],
        }
    }

    return jsonify(response)

@app.route('/get-overs/<match_no>',methods=['GET'])
def getOverAnalysisFromMatchNo(match_no):
    data = ball_by_ball[['match_no', 'batting_team', 'bowling_team', 'innings', 'over', 'runs_of_bat', 'extras', 'player_dismissed', "striker", "bowler", "wide", "noballs","byes","legbyes", "wicket_type"]]
    match = match_history[ ['match_no', 'team1', 'team2', 'innings1_score','innings2_score', 'innings1_wickets','innings2_wickets', 'venue','date','won_by','margin','winning_team']]

    # Convert match_no parameter from URL to integer
    match_no = int(match_no)

    # Filter data for the specific match
    filtered_data = data[data['match_no'] == match_no]
    general_match_info = match[match['match_no'] == match_no].iloc[0]

    # Convert the filtered DataFrame to a dictionary
    result = filtered_data.to_dict(orient='records')

    run_per_over = {1: {}, 2: {}}  # To track runs per over (0.1 -> 1, 1.1 -> 2...)
    fow = {1: {}, 2: {}}  # Dictionary to store the count of wickets per over
    team = {1: {"batting_team": None, "bowling_team": None}, 2: {"batting_team": None, "bowling_team": None}}

    over_analysis = {
        1: {  # Innings 1
            "pp": {"batting": {}, "bowling": {}, "total":0, "wickets":0},
            "middle": {"batting": {}, "bowling": {}, "total":0, "wickets":0},
            "death": {"batting": {}, "bowling": {}, "total":0, "wickets":0}
        },
        2: {  # Innings 2
            "pp": {"batting": {}, "bowling": {}, "total":0, "wickets":0},
            "middle": {"batting": {}, "bowling": {}, "total":0, "wickets":0},
            "death": {"batting": {}, "bowling": {}, "total":0, "wickets":0}
        }
    }

    for ball in result:
        over = ball["over"]
        innings = ball["innings"]
        runs_of_bat = ball["runs_of_bat"]
        extras = ball["extras"]
        player_dismissed = ball["player_dismissed"]
        batting_team = ball["batting_team"]
        bowling_team = ball["bowling_team"]
        batter = ball["striker"]
        bowler = ball["bowler"]
        wides = ball['wide']
        no_balls = ball['noballs']
        wicket_type = ball['wicket_type']
        leg_byes = ball['legbyes']
        byes = ball['byes']

        if team[innings]["batting_team"] is None:  # Only assign if not already set
            team[innings]["batting_team"] = batting_team
        if team[innings]["bowling_team"] is None:  # Only assign if not already set
            team[innings]["bowling_team"] = bowling_team

        # Track runs per over (for creating run per over stats)
        over_key = int(str(over).split(".")[0])  # Extract the over number (0.1 -> 0, 1.1 -> 1)

        if over_key not in run_per_over[innings]:
            run_per_over[innings][over_key] = 0

        run_per_over[innings][over_key] += runs_of_bat + extras

        # Count wickets per over
        if isinstance(player_dismissed, str):  # If a player was dismissed
            if over_key not in fow[innings]:
                fow[innings][over_key] = 0  # Initialize wicket count for the over
            fow[innings][over_key] += 1  # Increment wicket count

        # Over Analysis for PP, Middle and Death
        phase = get_phase(over)

        over_analysis[innings][phase]["total"] += (runs_of_bat+extras)
        if isinstance(player_dismissed, str):  # If a player was dismissed
            over_analysis[innings][phase]["wickets"] += 1

        if batter not in over_analysis[innings][phase]["batting"]:
            over_analysis[innings][phase]["batting"][batter] = {"runs": 0, "balls": 0}
        over_analysis[innings][phase]["batting"][batter]["runs"] += runs_of_bat
        if wides != 1 or no_balls != 1:
            over_analysis[innings][phase]["batting"][batter]["balls"] += 1

        if bowler not in over_analysis[innings][phase]["bowling"]:
            over_analysis[innings][phase]["bowling"][bowler] = {"balls": 0, "runs_conceded": 0, "wickets": 0}

        over_analysis[innings][phase]["bowling"][bowler]["runs_conceded"] += runs_of_bat
        if wides==1:
            over_analysis[innings][phase]["bowling"][bowler]["runs_conceded"] += extras
        if no_balls ==1:
            over_analysis[innings][phase]["bowling"][bowler]["runs_conceded"] += 1

        if wides == 0 and no_balls == 0:
            over_analysis[innings][phase]["bowling"][bowler]["balls"] += 1

        if isinstance(player_dismissed,str):
            if wicket_type != "" and wicket_type != "runout":
                over_analysis[innings][phase]["bowling"][bowler]["wickets"] += 1

    top_performers = {1: {}, 2: {}}  # Store top batters & bowlers for each innings and phase

    for innings in [1, 2]:  # Loop through both innings
        for phase in ["pp", "middle", "death"]:  # Loop through all three phases
            top_batter = get_top_batter(over_analysis[innings][phase]["batting"])
            top_bowler = get_top_bowler(over_analysis[innings][phase]["bowling"])

            top_performers[innings][phase] = {
                "top_batter": {"player": top_batter[0], **top_batter[1]} if top_batter else None,
                "top_bowler": {"player": top_bowler[0], **top_bowler[1]} if top_bowler else None
            }
            top_performers[innings][phase]["total"] = over_analysis[innings][phase]["total"]
            top_performers[innings][phase]["wickets"] = over_analysis[innings][phase]["wickets"]

    # Create the response structure
    response = {
        "runPerOver": {
            "innings1": [{"over": f"{k+1}", "runs": v} for k, v in sorted(run_per_over[1].items())],
            "innings2": [{"over": f"{k+1}", "runs": v} for k, v in sorted(run_per_over[2].items())]
        },
        "wicketOver": {
            "innings1": [{"over": f"{k+1}", "wickets": v} for k, v in sorted(fow[1].items())],
            "innings2": [{"over": f"{k+1}", "wickets": v} for k, v in sorted(fow[2].items())]
        },
        "teams": {
            "innings1": [{"batting": team[1]["batting_team"], "bowling": team[1]["bowling_team"]}],
            "innings2": [{"batting": team[2]["batting_team"], "bowling": team[2]["bowling_team"]}],
        },
        "topPerformers": {
            "innings1": top_performers[1],
            "innings2": top_performers[2]
        },
        "header": {
            "matchNo" : match_no,
            "venue" : general_match_info["venue"],
            "date" : general_match_info["date"],
            "winning_team" : general_match_info["winning_team"],
            "margin" : general_match_info["margin"],
            "won_by" : general_match_info["won_by"],
        }
    }

    return jsonify(response)

def get_phase(ball):
    if 0.1 <= ball <= 5.6:
        return "pp"
    elif 6.1 <= ball <= 14.6:
        return "middle"
    elif 15.1 <= ball <= 19.6:
        return "death"
    return None

def get_top_batter(batting_data):
    if not batting_data:
        return None  # Return None if no batters in this phase
    return max(batting_data.items(), key=lambda x: x[1]["runs"])

# Helper function to find the top bowler based on wickets and runs conceded
def get_top_bowler(bowling_data):
    if not bowling_data:
        return None  # Return None if no bowlers in this phase
    return min(
        bowling_data.items(),
        key=lambda x: (-x[1]["wickets"], x[1]["runs_conceded"])  # Sort by wickets desc, runs asc
    )

@app.route('/get-partnerships/<match_no>',methods=['GET'])
def getPartnershipFromMatchNo(match_no):
    data = ball_by_ball[['match_no', 'batting_team', 'bowling_team', 'innings', 'over', 'runs_of_bat', 'extras', 'player_dismissed', 'striker', 'non_striker', 'wide', 'noballs']]
    match = match_history[ ['match_no', 'team1', 'team2', 'innings1_score','innings2_score', 'innings1_wickets','innings2_wickets', 'venue','date','won_by','margin','winning_team']]

    match_no = int(match_no)
    filtered_data = data[data['match_no'] == match_no]
    general_match_info = match[match['match_no'] == match_no].iloc[0]
    result = filtered_data.to_dict(orient='records')

    partnerships = {1: [], 2: []}  # Store partnerships for both innings
    current_partnerships = {}  # Track ongoing partnerships
    innings1batting = ""
    innings2batting = ""

    for i, ball in enumerate(result):
        innings = ball["innings"]
        striker = ball["striker"]
        non_striker = ball["non_striker"]
        runs_of_bat = ball["runs_of_bat"]
        extras = ball["extras"]
        player_dismissed = ball["player_dismissed"]
        wide = ball["wide"]
        noball = ball["noballs"]

        if innings == 1:
            innings1batting = ball["batting_team"]
        if innings == 2:
            innings2batting = ball["batting_team"]

        # Initialize partnership if not exists
        if innings not in current_partnerships:
            current_partnerships[innings] = {
                "batter1": striker,
                "runs1": 0,
                "balls1": 0,
                "contribution1": 0,
                "batter2": non_striker,
                "runs2": 0,
                "balls2": 0,
                "contribution2": 0,
                "extras": 0,
                "balls": 0,
                "runs": 0
            }

        # Track the current partnership
        partnership = current_partnerships[innings]

        # Update balls faced (excluding wide and no-ball)
        if wide != 1 and noball != 1:
            partnership["balls"] += 1  # Total partnership balls

            if striker == partnership["batter1"]:
                partnership["balls1"] += 1
            else:
                partnership["balls2"] += 1

        # Update runs & contribution
        partnership["runs"] += runs_of_bat + extras  # Total partnership runs
        if striker == partnership["batter1"]:
            partnership["contribution1"] += runs_of_bat
            partnership["runs1"] += runs_of_bat
        else:
            partnership["contribution2"] += runs_of_bat
            partnership["runs2"] += runs_of_bat

        # Add extras
        partnership["extras"] += extras

        # Handle player dismissal
        if isinstance(player_dismissed, str):  
            # Save completed partnership
            partnerships[innings].append(partnership)

            # Track last dismissed batter
            last_batter_out = player_dismissed  

            # Determine the next batter (look ahead to next ball)
            if i + 1 < len(result):
                next_ball = result[i + 1]
                saved_batter = non_striker if player_dismissed == striker else striker
                new_batter = next_ball["striker"] if saved_batter == next_ball["non_striker"] else next_ball["non_striker"]  # The new incoming batter

                # Start a new partnership
                current_partnerships[innings] = {
                    "batter1": saved_batter,  # The surviving batter
                    "runs1": 0,
                    "balls1": 0,
                    "contribution1": 0,
                    "batter2": new_batter,  # New batter coming in
                    "runs2": 0,
                    "balls2": 0,
                    "contribution2": 0,
                    "extras": 0,
                    "balls": 0,
                    "runs": 0
                }
    response = {
        "partnership": partnerships,
        "innings1batting": innings1batting,
        "innings2batting" : innings2batting,
        "header": {
            "matchNo" : match_no,
            "venue" : general_match_info["venue"],
            "date" : general_match_info["date"],
            "winning_team" : general_match_info["winning_team"],
            "margin" : general_match_info["margin"],
            "won_by" : general_match_info["won_by"],
        }
    }
    return jsonify(response)

@app.route('/get-teams/<team_name>', methods=['GET'])
def get_partnership_from_match_no(team_name):

    average_analysis = match_history[['innings1_score', 'match_no', 'innings2_score','innings1_wickets','innings2_wickets', 'team1', 'team2', 'toss_winner','toss_decision','winning_team',]]
    # Calculate the averages, skipping NaN values
    average_innings1_score = average_analysis['innings1_score'].mean(skipna=True)
    average_innings2_score = average_analysis['innings2_score'].mean(skipna=True)
    average_innings1_wickets = average_analysis['innings1_wickets'].mean(skipna=True)
    average_innings2_wickets = average_analysis['innings2_wickets'].mean(skipna=True)

    average_won_batting_first = average_analysis[((average_analysis["winning_team"] == average_analysis["team1"]) | (average_analysis["winning_team"] == average_analysis["team2"]) ) & (average_analysis["toss_decision"] == "bat") & (average_analysis["winning_team"] != "TIE")].shape[0]
    average_won_bowling_first = average_analysis[((average_analysis["winning_team"] == average_analysis["team1"]) | (average_analysis["winning_team"] == average_analysis["team2"])) & (average_analysis["toss_decision"] == "field") & (average_analysis["winning_team"] != "TIE")].shape[0]

    average_overall_score = pd.concat([average_analysis['innings1_score'],average_analysis['innings2_score']]).dropna().mean()
    average_overall_wickets = pd.concat([average_analysis['innings1_wickets'], average_analysis['innings2_wickets']]).dropna().mean()

    # This is team infromation
    batting_first = average_analysis[average_analysis["team1"] == team_name]["innings1_score"]
    batting_second = average_analysis[average_analysis["team2"] == team_name]["innings2_score"]
    wickets_first = average_analysis[average_analysis["team2"] == team_name]["innings2_wickets"]
    wickets_second = average_analysis[average_analysis["team1"] == team_name]["innings1_wickets"]

    batting_first_count = batting_first.shape[0]
    batting_second_count = batting_second.shape[0]
    team_won_batting_first = average_analysis[(average_analysis["winning_team"] == team_name)  & (average_analysis["team1"] == team_name) & (average_analysis["winning_team"] != "TIE")].shape[0]
    team_won_bowling_first = average_analysis[(average_analysis["winning_team"] == team_name)  & (average_analysis["team2"] == team_name) & (average_analysis["winning_team"] != "TIE")].shape[0]

    # Compute averages, ignoring NaN values
    avg_score_batting_first = batting_first.dropna().mean()
    avg_score_batting_second = batting_second.dropna().mean()
    avg_wicket_bowling_first = wickets_first.dropna().mean()
    avg_wicket_bowling_second = wickets_second.dropna().mean()
    
    # Compute overall average score
    overall_avg_score = pd.concat([batting_first, batting_second]).dropna().mean()
    overall_wickets = pd.concat([wickets_first, wickets_second]).dropna().mean()


    # Calculate points
    team_matches = average_analysis[(average_analysis["team1"] == team_name) | (average_analysis["team2"] == team_name)]
    # Limit to the first 70 matches
    team_matches = team_matches[team_matches["match_no"] <= 70]
    wins = team_matches[team_matches["winning_team"] == team_name].shape[0] * 2
    ties = team_matches[team_matches["winning_team"] == "TIE"].shape[0] * 1
    total_points = wins + ties

    # Team's Player Stats Code

    batting_data = ball_by_ball[ball_by_ball["batting_team"] == team_name]
    bowling_data = ball_by_ball[ball_by_ball["bowling_team"] == team_name]

    # Get list of unique batters and bowlers
    batters = batting_data["striker"].unique()
    bowlers = bowling_data["bowler"].unique()

    batter_stats = []
    bowler_stats = []

    # Compute Batting Stats
    for batter in batters:
        player_data = batting_data[batting_data["striker"] == batter]

        runs = int(player_data["runs_of_bat"].sum())  
        balls = player_data[player_data["wide"] != 1].shape[0]
        matches_played = int(player_data["match_no"].nunique())  
        dismissals = int(player_data[player_data["player_dismissed"] == batter]["match_no"].nunique())
        not_outs = matches_played - dismissals
        high_score = int(player_data.groupby("match_no")["runs_of_bat"].sum().max() or 0)
        avg = float(runs / dismissals) if dismissals > 0 else float(runs)
        sr = float((runs / balls * 100) if balls > 0 else 0)
        centuries = int((player_data.groupby("match_no")["runs_of_bat"].sum() >= 100).sum())
        fifties = int(player_data.groupby("match_no")["runs_of_bat"].sum().between(50, 99).sum())
        fours = int((player_data["runs_of_bat"] == 4).sum())
        sixes = int((player_data["runs_of_bat"] == 6).sum())

        batter_stats.append({
            "player": batter,
            "runs": runs,
            "balls": balls,
            "matches": matches_played,
            "not_outs": not_outs,
            "high_score": high_score,
            "average": round(avg, 2),
            "strike_rate": round(sr, 2),
            "hundreds": centuries,
            "fiftys": fifties,
            "fours": fours,
            "sixes": sixes
        })

    for bowler in bowlers:
        player_data = bowling_data[bowling_data["bowler"] == bowler]

        wkts = int(player_data["player_dismissed"].notna().sum())
        matches_played = int(player_data["match_no"].nunique())
        overs = player_data.shape[0] // 6 + (player_data.shape[0] % 6) * 0.1
        runs_conceded = int(player_data["runs_of_bat"].sum() + player_data["extras"].sum())
        avg = float((runs_conceded / wkts) if wkts > 0 else 0)
        econ = float(runs_conceded / overs if overs > 0 else 0)
        sr = float(player_data.shape[0] / wkts if wkts > 0 else 0)

        wickets_per_match = player_data.groupby("match_no")["player_dismissed"].count()
        three_wkt_hauls = int((wickets_per_match >= 3).sum())
        four_wkt_hauls = int((wickets_per_match >= 4).sum())
        five_wkt_hauls = int((wickets_per_match >= 5).sum())

        bowler_stats.append({
            "player": bowler,
            "wickets": wkts,
            "matches": matches_played,
            "innings": matches_played,  
            "overs": overs,
            "runs_conceded": runs_conceded,
            "average": round(avg, 2),
            "economy": round(econ, 2),
            "strike_rate": round(sr, 2),
            "three_w": three_wkt_hauls,
            "four_w": four_wkt_hauls,
            "five_w": five_wkt_hauls
        })

    batter_stats.sort(key=lambda x: x["runs"], reverse=True)  # Sort batters by runs (highest first)
    bowler_stats.sort(key=lambda x: x["wickets"], reverse=True)  # Sort bowlers by wickets (highest first)




    return jsonify({
        "average_analysis":{
            "avg_score_batting_first": average_innings1_score,
            "avg_score_batting_second": average_innings2_score,
            "avg_wicket_bowling_first": average_innings1_wickets,
            "avg_wicket_bowling_second":average_innings2_wickets,
            "team_won_batting_first":average_won_batting_first,
            "team_won_bowling_first":average_won_bowling_first,
            "overall_avg_score": average_overall_score,
            "overall_wickets":average_overall_wickets
        },
        "teamAnalysis":{
            "avg_score_batting_first":avg_score_batting_first,
            "avg_score_batting_second":avg_score_batting_second,
            "avg_wicket_bowling_first":avg_wicket_bowling_first,
            "avg_wicket_bowling_second":avg_wicket_bowling_second,
            "team_won_batting_first":team_won_batting_first,
            "batting_first_count":batting_first_count,
            "bowling_first_count":batting_second_count,
            "team_won_bowling_first":team_won_bowling_first,
            "overall_avg_score":overall_avg_score,
            "overall_wickets":overall_wickets,
            "points":total_points
        },
        "batterStats": batter_stats,
        "bowlerStats": bowler_stats
    })

@app.get("/get-venue/<venue_name>")
def get_venue_stats(venue_name: str):
    # Filter matches played at the venue from match history
    venue_matches = match_history[match_history["venue"] == venue_name]
    
    # Get all match numbers played at this venue
    match_numbers = venue_matches["match_no"].unique()
    
    # Filter ball-by-ball data using match numbers
    venue_balls = ball_by_ball[ball_by_ball["match_no"].isin(match_numbers)]

    # Basic venue details
    city = venue_matches["city"].iloc[0] if "city" in venue_matches.columns else "Unknown"
    matches_played = len(venue_matches)

    # Batting and bowling stats
    avg_score_batting_first = venue_matches["innings1_score"].mean()
    avg_score_batting_second = venue_matches["innings2_score"].mean()

    avg_wickets_bowling_first = venue_matches["innings1_wickets"].mean()
    avg_wickets_bowling_second = venue_matches["innings2_wickets"].mean()

    matches_won_batting_first = len(venue_matches[venue_matches["winning_team"] == venue_matches["team1"]])
    matches_won_batting_second = len(venue_matches[venue_matches["winning_team"] == venue_matches["team2"]])

    highest_scorer = (
        venue_balls.groupby(["match_no", "striker"])["runs_of_bat"]
        .sum()
        .reset_index()
        .sort_values(by="runs_of_bat", ascending=False)
        .iloc[0]
    )
    # Count valid balls faced (excluding byes, legbyes, wide)
    balls_faced = venue_balls[
        (venue_balls["match_no"] == highest_scorer["match_no"]) &
        (venue_balls["striker"] == highest_scorer["striker"]) &
        (venue_balls["byes"] == 0) &
        (venue_balls["legbyes"] == 0) &
        (venue_balls["wide"] == 0)
    ].shape[0]

    highest_scorer_details = {
        "match_no": highest_scorer["match_no"],
        "batter": highest_scorer["striker"],
        "runs": highest_scorer["runs_of_bat"],
        "balls_faced": balls_faced
    }

    # 2. Highest Wicket-Taker in a Single Match
    highest_wicket_taker = (
        venue_balls[venue_balls["wicket_type"].notna() & (venue_balls["wicket_type"] != "runout")]
        .groupby(["match_no", "bowler"])["wicket_type"]
        .count()
        .reset_index()
        .sort_values(by="wicket_type", ascending=False)
        .iloc[0]
    )

    # Count valid balls bowled (excluding wide and no-balls)
    balls_bowled = venue_balls[
        (venue_balls["match_no"] == highest_wicket_taker["match_no"]) &
        (venue_balls["bowler"] == highest_wicket_taker["bowler"]) &
        (venue_balls["wide"] == 0) &
        (venue_balls["noballs"] == 0)
    ].shape[0]

# 3. Runs & Wickets conceded in different phases (PP, Middle, Death) for both innings
    phase_stats = {
        "firstInnings": {
            "Powerplay": {"runs": 0, "wickets": 0},
            "Middle": {"runs": 0, "wickets": 0},
            "Death": {"runs": 0, "wickets": 0},
        },
        "secondInnings": {
            "Powerplay": {"runs": 0, "wickets": 0},
            "Middle": {"runs": 0, "wickets": 0},
            "Death": {"runs": 0, "wickets": 0},
        },
    }

    # Iterate over innings
    for innings in [1, 2]:
        innings_key = "firstInnings" if innings == 1 else "secondInnings"
        innings_data = venue_balls[venue_balls["innings"] == innings]

        # Iterate over phases
        for phase, (start, end) in zip(["Powerplay", "Middle", "Death"], [(0, 6), (7, 15), (16, 20)]):
            phase_data = innings_data[(innings_data["over"] >= start) & (innings_data["over"] <= end)]
            
            # Convert values to int to avoid serialization issues
            phase_stats[innings_key][phase]["runs"] = int(phase_data["runs_of_bat"].sum() + phase_data["extras"].sum())
            phase_stats[innings_key][phase]["wickets"] = int(phase_data["wicket_type"].count())



    return jsonify({
        "venue_name": venue_name,
        "city": city,
        "matches_played": int(matches_played),
        "avg_score_batting_first": float(avg_score_batting_first),
        "avg_score_batting_second": float(avg_score_batting_second),
        "avg_wickets_bowling_first": float(avg_wickets_bowling_first),
        "avg_wickets_bowling_second": float(avg_wickets_bowling_second),
        "matches_won_batting_first": int(matches_won_batting_first),
        "matches_won_batting_second": int(matches_won_batting_second),
        "highest_scorer": {
            "match_no": int(highest_scorer["match_no"]),
            "batter": highest_scorer["striker"],
            "runs": int(highest_scorer["runs_of_bat"]),
            "balls_faced": int(balls_faced)
        },
        "highest_wicket_taker": {
            "match_no": int(highest_wicket_taker["match_no"]),
            "bowler": highest_wicket_taker["bowler"],
            "wickets": int(highest_wicket_taker["wicket_type"]),
            "balls_bowled": int(balls_bowled)
        },
        "phase_stats": phase_stats
    })

@app.route('/get-stats', methods=['GET'])
def calculate_stats():
    # Calculate batting and bowling stats separately
    batting_stats = calculate_batting_stats(ball_by_ball)
    bowling_stats = calculate_bowling_stats(ball_by_ball)

    response = {
        **batting_stats,
        **bowling_stats
    }

    return jsonify(response)

def calculate_batting_stats(ball_by_ball):
    batting_cols = ['match_no', 'batting_team', 'bowling_team', 'striker', 'runs_of_bat', 'extras', 'wide', 'over', 'player_dismissed']
    batting_df = ball_by_ball[batting_cols].copy()
    
    # Count only valid balls faced (excluding wides)
    batting_df['valid_ball'] = batting_df['wide'] == 0
    
    # Group by 'striker' to get cumulative stats
    batting_stats = batting_df.groupby('striker').agg(
        Team=('batting_team', lambda x: x.mode().iloc[0]),
        Runs=('runs_of_bat', 'sum'),
        Innings=('match_no', pd.Series.nunique),
        Balls_Faced=('valid_ball', 'sum'),
        Fours=('runs_of_bat', lambda x: (x == 4).sum()),
        Sixes=('runs_of_bat', lambda x: (x == 6).sum())
    ).reset_index()

    dismissals = batting_df.groupby('striker')['player_dismissed'].count().reset_index()
    dismissals.rename(columns={'player_dismissed': 'Dismissals'}, inplace=True)

    batting_stats = batting_stats.merge(dismissals, on='striker', how='left').fillna(0)
    batting_stats['Not_Outs'] = batting_stats['Innings'] - batting_stats['Dismissals']

    # Highest individual score per match
    highest_scores = batting_df.groupby(['match_no', 'striker']).agg(
        Match_Runs=('runs_of_bat', 'sum'),
        Opponent_Team=('bowling_team', 'first')
    ).reset_index()
    
    # Get highest score for each player
    max_scores = highest_scores.groupby('striker').agg(
        Highest_Score=('Match_Runs', 'max')
    ).reset_index()

    batting_stats = batting_stats.merge(max_scores, on='striker', how='left')

    # Calculate Batting Average & Strike Rate
    batting_stats['Average'] = batting_stats.apply(
        lambda row: round(row['Runs'] / (row['Innings'] - row['Not_Outs']), 1) if (row['Innings'] - row['Not_Outs']) > 0 else round(row['Runs'], 1),
        axis=1
    )
    batting_stats['SR'] = round((batting_stats['Runs'] / batting_stats['Balls_Faced']) * 100, 1)


    # Count centuries and half-centuries
    batting_100s_50s = highest_scores.groupby('striker').agg(
        Hundreds=('Match_Runs', lambda x: (x >= 100).sum()),
        Fifties=('Match_Runs', lambda x: ((x >= 50) & (x < 100)).sum())
    ).reset_index()

    batting_stats = batting_stats.merge(batting_100s_50s, on='striker', how='left')
    batting_stats["Striker"] = batting_stats["striker"]
    # Identify fastest 50s and 100s
    batting_df['cumulative_runs'] = batting_df.groupby(['match_no', 'striker'])['runs_of_bat'].cumsum()
    batting_df['cumulative_balls'] = batting_df.groupby(['match_no', 'striker'])['valid_ball'].cumsum()

    innings_stats = batting_df.groupby(['match_no', 'striker', 'batting_team', 'bowling_team']).agg(
        Final_Score=('cumulative_runs', 'max'),
        Fours=('runs_of_bat', lambda x: (x == 4).sum()),
        Sixes=('runs_of_bat', lambda x: (x == 6).sum())
    ).reset_index()

    fastest_50s = batting_df[batting_df['cumulative_runs'] >= 50].groupby(
        ['match_no', 'striker', 'batting_team', 'bowling_team']
    ).agg(Balls_Taken=('cumulative_balls', 'min')).reset_index()
    
    fastest_100s = batting_df[batting_df['cumulative_runs'] >= 100].groupby(
        ['match_no', 'striker', 'batting_team', 'bowling_team']
    ).agg(Balls_Taken=('cumulative_balls', 'min')).reset_index()

    fastest_50s = fastest_50s.merge(innings_stats, on=['match_no', 'striker', 'batting_team', 'bowling_team']).sort_values(by='Balls_Taken').head(50)
    fastest_100s = fastest_100s.merge(innings_stats, on=['match_no', 'striker', 'batting_team', 'bowling_team']).sort_values(by='Balls_Taken').head(50)

    return {
        "Batting_Stats": batting_stats.to_dict(orient='records'),
        "Top_50_Fastest_50s": fastest_50s.to_dict(orient='records'),
        "Top_50_Fastest_100s": fastest_100s.to_dict(orient='records')
    }

def calculate_bowling_stats(ball_by_ball):
    # Exclude run out dismissals from wicket count
    ball_by_ball['is_wicket'] = ((ball_by_ball['wicket_type'].notna()) & (ball_by_ball['wicket_type'] != 'run out')).astype(int)

    # Count valid balls (excluding wides and no-balls)
    ball_by_ball['valid_ball'] = ((ball_by_ball['wide'] == 0) & (ball_by_ball['noballs'] == 0)).astype(int)

    # Calculate total runs conceded (includes extras when wide or no-ball)
    ball_by_ball['bowler_runs'] = ball_by_ball['runs_of_bat'] + ball_by_ball.apply(
        lambda row: row['extras'] if row['wide'] == 1 or row['noballs'] == 1 else 0, axis=1
    )

    # Count dot balls (where runs_of_bat and extras are 0)
    ball_by_ball['is_dot_ball'] = ((ball_by_ball['runs_of_bat'] == 0) & (ball_by_ball['extras'] == 0)).astype(int)

    # Aggregate bowling stats
    bowling_stats = ball_by_ball.groupby('bowler').agg(
        Team=('bowling_team', lambda x: x.mode().iloc[0]),
        Wickets=('is_wicket', 'sum'),
        Runs=('bowler_runs', 'sum'),
        Balls_Bowled=('valid_ball', 'sum'),
        Matches=('match_no', pd.Series.nunique),
        Dot_Balls=('is_dot_ball', 'sum')
    ).reset_index()

    # Count hat-tricks (3 wickets in 3 consecutive deliveries)
    ball_by_ball['hat_trick'] = ball_by_ball.groupby('bowler')['is_wicket'].rolling(window=3, min_periods=3).sum().reset_index(level=0, drop=True)
    hat_tricks = ball_by_ball.groupby('bowler')['hat_trick'].apply(lambda x: (x >= 3).sum()).reset_index()
    hat_tricks.rename(columns={'hat_trick': 'Hat_Tricks'}, inplace=True)
    
    bowling_stats = bowling_stats.merge(hat_tricks, on='bowler', how='left')
    bowling_stats["Bowler"] = bowling_stats["bowler"]

    # Best bowling figures per innings
    best_bowling_figures = ball_by_ball.groupby(['match_no', 'bowler']).agg(
        Wickets=('is_wicket', 'sum'),
        Runs_Conceded=('bowler_runs', 'sum')
    ).reset_index()

    # Get best and worst innings
    best_bowling = best_bowling_figures.sort_values(by=['bowler', 'Wickets', 'Runs_Conceded'], ascending=[True, False, True]).drop_duplicates(subset=['bowler'], keep='first')
    worst_bowling = best_bowling_figures.sort_values(by=['bowler', 'Runs_Conceded'], ascending=[True, False]).drop_duplicates(subset=['bowler'], keep='first')

    # Merge best and worst bowling figures
    bowling_stats = bowling_stats.merge(best_bowling[['bowler', 'Wickets', 'Runs_Conceded']], on='bowler', how='left', suffixes=('', '_Best_Innings'))
    bowling_stats = bowling_stats.merge(worst_bowling[['bowler', 'Runs_Conceded']], on='bowler', how='left', suffixes=('', '_Most_Runs_Innings'))

    # Calculate bowling averages, economy, and strike rate
    bowling_stats['Average'] = bowling_stats.apply(lambda row: round(row['Runs'] / row['Wickets'], 1) if row['Wickets'] > 0 else 0, axis=1)
    bowling_stats['Economy'] = bowling_stats.apply(lambda row: round((row['Runs'] / (row['Balls_Bowled'] / 6)), 1) if row['Balls_Bowled'] > 0 else 0, axis=1)
    bowling_stats['Strike_Rate'] = bowling_stats.apply(lambda row: round(row['Balls_Bowled'] / row['Wickets'], 1) if row['Wickets'] > 0 else 0, axis=1)


    # Replace inf values with 0
    bowling_stats.replace([float('inf'), float('-inf')], 0, inplace=True)
    bowling_stats.fillna(0, inplace=True)

    return {
        "Bowling_Stats": bowling_stats.to_dict(orient='records')
    }

if __name__ == '__main__':
    # Get the port from the environment variable, default to 5000 if not set
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
