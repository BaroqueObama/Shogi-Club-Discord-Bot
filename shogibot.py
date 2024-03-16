#!/usr/bin/env python
# coding: utf-8

# # HHS Shogi Club Discord Bot

# #### These are import statements

# In[1]:


import discord
from discord.ext import commands
from discord import app_commands

import pandas as pd
import numpy as np
from datetime import datetime
import math
import typing
from typing import Literal
import matplotlib.pyplot as plt
from datetime import timedelta
import ast



# In[2]:


class ShogiClub:
    def __init__(self, test=False):
        # Whether I'm just testing my code or not
        self.test = test
        
        # Reads data from csv files and initializes DataFrames
        self.players = pd.read_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/players.csv")
        self.players.columns.name = "players"

        self.games = pd.read_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/games.csv")
        self.games.columns.name = "games"

        self.player_history = pd.read_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/player_history.csv")
        self.player_history.columns.name = "player_history"
        
        self.log_games = []
        self.log_players = []
        self.log_player_history = []
        self.log_comments = []
        
    # Saves dataframe as a csv file
    def save(self, df):
        df.to_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/" + df.columns.name + ".csv", index=False)
    
    # Determines if ShogiClub is ready to update scores or not
    def ready_to_update(self):
        if not (self.log_games and self.log_players):
            return False
        else:
            return True
    
    # Sets up log to allow for updating
    def begin_update(self):
        self.log_games = [self.games.copy()]
        self.log_players = [self.players.copy()]
        self.log_player_history = [self.player_history.copy()]
        self.log_comments = ["Beginning state"]
    
    # Saves dataframes and closes log to end updating.
    def end_update(self):
        self.save(self.players)
        self.save(self.games)
        self.save(self.player_history)
        self.log_games = []
        self.log_players = []
        self.log_player_history = []
        self.log_comments = []
    
    # Rollsback data to certain index
    def rollback_data(self, index):
        self.players = self.log_players[index].copy()
        self.games = self.log_games[index].copy()
        self.player_history = self.log_player_history[index].copy()
        
    # Adds current player data to player_history
    def append_player_data(self, date):
        for col in self.player_history.columns[2:]:
            self.player_history[col] = self.player_history[col].apply(lambda x: eval(x, {"inf": np.inf, "nan": np.nan}))
        for index, player in self.players.iterrows():
            # Gets index of player in player history
            player_data_index = self.player_history[self.player_history["nick_name"]==player["nick_name"]].index
            # If new player
            if player_data_index.empty:
                self.append_data(self.player_history, player["nick_name"], player["full_name"], [player["win"]], [player["loss"]], [player["draw"]], [player["total"]], [player["kd"]], [player["win_rate"]], [player["ELO"]], [date])
            else:
                self.player_history.at[player_data_index[0], "date"].append(date)
                for column_name in player.index.values.tolist()[2:]:
                    self.player_history.at[player_data_index[0], column_name].append(player[column_name])
    
    # Helper Adds row of data to dataframe
    def append_data(self, df, *args):
        df.loc[len(df)] = args
    
    # Adds new log
    def add_log(self, comment):
        self.log_games.append(self.games.copy())
        self.log_players.append(self.players.copy())
        self.log_player_history.append(self.player_history.copy())
        self.log_comments.append(comment)
    
    # Returns nick name. If doesn't exist, return False
    def get_nick_name(self, name):
        if self.players["nick_name"].isin([name]).any():
            return name
        elif self.players["full_name"].isin([name]).any():
            return self.players[self.players["full_name"] == name]["nick_name"].values[0]
        else:
            return False
    
    # Returns usable nickname for new players
    def new_nick_name(self, full_name):
        name_parts = full_name.split()
        if not self.players["nick_name"].isin([name_parts[0]]).any():
            return name_parts[0]
        else:
            nick_name = name_parts[0]
            i = 0
            while self.players["nick_name"].isin([nick_name]).any():
                nick_name = full_name[0 : len(name_parts[0])+2+i].replace(" ", "_")
                i += 1
            return nick_name
        
    # Adds a new player
    def add_new_player(self, nick_name, full_name, elo):
        self.append_data(self.players, nick_name, full_name, 0, 0, 0, 0, 0, 0, elo)
    
    # Updates Player data based on game
    def update_game_players(self, nick1, nick2, result1, result2, delta_elo1, delta_elo2):
        # Adjust win, loss, draw
        # result1, result2 is "win", "loss", "draw"
        self.set_player_stat(nick1, result1, self.get_player_stat(nick1, result1)+1)
        self.set_player_stat(nick1, "total", self.get_player_stat(nick1, "total")+1)
        self.set_player_stat(nick2, result2, self.get_player_stat(nick2, result2)+1)
        self.set_player_stat(nick2, "total", self.get_player_stat(nick2, "total")+1)
        
        # Adjust kd and rate
        self.set_player_stat(nick1, "kd", self.get_player_stat(nick1, "win")/self.get_player_stat(nick1, "loss"))
        self.set_player_stat(nick1, "win_rate", self.get_player_stat(nick1, "win")/self.get_player_stat(nick1, "total"))
        self.set_player_stat(nick2, "kd", self.get_player_stat(nick2, "win")/self.get_player_stat(nick2, "loss"))
        self.set_player_stat(nick2, "win_rate", self.get_player_stat(nick2, "win")/self.get_player_stat(nick2, "total"))
        
        # Update ELO
        self.set_player_stat(nick1, "ELO", self.get_player_stat(nick1,"ELO")+delta_elo1)
        self.set_player_stat(nick2, "ELO", self.get_player_stat(nick2,"ELO")+delta_elo2)
    
    # Updates a player's stat to a value
    def set_player_stat(self, nick_name, stat, value):
        self.players.loc[self.players.index[self.players["nick_name"] == nick_name], stat] = value
    
    # Get's a player's stat
    def get_player_stat(self, nick_name, stat):
        return self.players.loc[self.players.index[self.players["nick_name"] == nick_name], stat].values[0]
        #return self.players.loc[self.players.index[self.players["nick_name"] == name],"ELO"].values[0]
    
    # Returns K constant by ELO
    def get_K(self, ELO):
        return 194.491 * math.exp(-0.000888269 * ELO)
    
    # Returns expected win from ELO
    def expected(self, ELO1, ELO2):
        return 1 / (1 + 10 ** ((ELO2 - ELO1) / 400))
    
    # Returns the new ELO for the two players
    def new_elo(self, name1, name2, result1, result2):
        ELO1 = self.get_player_stat(name1, "ELO")
        ELO2 = self.get_player_stat(name2, "ELO")
        change1 = self.get_K(ELO1) * (result1 - self.expected(ELO1, ELO2))
        change2 = self.get_K(ELO2) * (result2 - self.expected(ELO2, ELO1))
        return (change1, change2)
    
    # Adds new game and updates players
    def add_game(self, name1, name2, game_mode, result, comments, date):
        ELO1 = self.get_player_stat(name1, "ELO")
        ELO2 = self.get_player_stat(name2, "ELO")
        expectation = self.expected(ELO1, ELO2)
        change_elo1 = 0
        change_elo2 = 0
        
        # Adjust change elo if ranked
        if game_mode.upper() == "R":
            if result.upper() == "W":
                change_elo1, change_elo2 = self.new_elo(name1, name2, 1, 0)
            elif result.upper() == "L":
                change_elo1, change_elo2 = self.new_elo(name1, name2, 0, 1)
        
        # Add data to games
        self.append_data(self.games, name1, name2, game_mode.upper(), result.upper(), date, expectation, ELO1, ELO2, change_elo1, change_elo2, comments)
        # Update Players
        translate_results = {"W":("win", "loss"), "L":("loss", "win"), "D":("draw", "draw")}
        result1, result2 = translate_results[result.upper()]
        self.update_game_players(name1, name2, result1, result2, change_elo1, change_elo2)
        
        return [result1, result2, ELO1 + change_elo1, ELO2 + change_elo2, change_elo1, change_elo2]
    
        # Formats some values to specific decimals
    def format_float(self, num):
        return f"{num:.1f}"
    
    def rerun_game_calculations(self):
        aux_games = self.games.copy()
        self.games = pd.read_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/reset_games.csv")
        self.games.columns.name = "games"
        self.player_history = pd.read_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/reset_player_history.csv")
        self.player_history.columns.name = "player_history"
        prev_date = aux_games.loc[0, "date"]
        for index, game in aux_games.iterrows():
            if prev_date != game["date"]:
                self.append_player_data(prev_date)
            prev_date = game["date"]
            self.add_game(game["name1"], game["name2"], game["game_mode"], game["result"], game["comments"], game["date"])
        self.append_player_data(prev_date)
            
    def clear_players(self):
        aux_players = self.players.copy()
        self.players = pd.read_csv((not self.test)*"Shogi-Club-Discord-Bot/"+"data/reset_players.csv")
        self.players.columns.name = "players"

        for index, player in aux_players.iterrows():
            self.add_new_player(player["nick_name"], player["full_name"], 1500)
        
    # Get list of continuous dates
    def get_continuous_dates(self, date_list, rank_list):
        x = []
        y = []
        
        date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in date_list]
        index =  date_objects[0]
        i = 0
        while index <= date_objects[-1]:
            x.append(index)
            if index == date_objects[i+1]:
                i += 1
            y.append(rank_list[i])
            index = index + timedelta(days=1)
        return (x, y)
        
    # Creates graph of top n players ranking changes
    def graph_players(self, rank_by, n):
        column_names = {"elo":"ELO", "games":"total", "kd":"kd", "rate":"win_rate"}
        pretty_names = {"elo":"ELO", "games":"# Played", "kd":"K/D", "rate":"% Won"}
        sorted_rankings = self.players.sort_values(by=column_names[rank_by], ascending=False)["nick_name"][0:n]
        player_data = self.player_history.iloc[list(sorted_rankings.index)]
        fig, ax = plt.subplots()
        
        smallest_date = datetime(2050, 1, 1)
        largest_date = datetime(2000, 1, 1)
        for index, player in player_data.iterrows():
            x, y = self.get_continuous_dates(ast.literal_eval(str(player["date"])), ast.literal_eval(str(player[column_names[rank_by]])))
            if x[0] < smallest_date:
                smallest_date = x[0]
            if x[-1] > largest_date:
                largest_date = x[-1]
            ax.plot(x, y, label=player["nick_name"])
        dates = pd.date_range(start=smallest_date, end=largest_date, periods=5)
        date_list = list(dates.to_pydatetime())
        ax.set_xticks(date_list)
        ax.set_title(f'Top {n} Players: {pretty_names[rank_by]} Ranking')
        ax.set_ylabel(pretty_names[rank_by])
        ax.set_xlabel('Date')
        ax.legend()
        fig.savefig((not self.test)*"Shogi-Club-Discord-Bot/"+'images/ranking.png', dpi=300)
        
        


# #### Initializing bot object

# In[2]:


description = '''Howdy I'm the Shogi club bot.

Here's some stuff I can do:'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='?', description=description, intents=intents)
shogi_club = ShogiClub(test=False)
plt.style.use("https://github.com/dhaitz/matplotlib-stylesheets/raw/master/pitayasmoothie-dark.mplstyle")


# #### Runs when bot is booted up

# In[3]:


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


# # Bot Features

# ### Bot Commands

# In[ ]:


# Begins update process on scores (so that changes can be rolled back easily)
@bot.command()
@commands.is_owner()
async def update(ctx, change):
    """Begins update process: \"begin\" or \"save\""""
    if change == "begin":
        if shogi_club.ready_to_update():
            await ctx.send("ShogiClub already ready to update scores.")
        else:
            shogi_club.begin_update()
            await ctx.send("ShogiClub ready to update scores.")
            
    elif change == "save":
        if shogi_club.ready_to_update():
            shogi_club.end_update()
            await ctx.send("ShogiClub scores updated and saved.")
        else:
            await ctx.send("ShogiClub not ready to update scores.")
    else:
        await ctx.send("Invalid option. Pick either \"begin\" to begin or \"save\" to save score update.")


# In[ ]:


# Rolls back changes made during update session
@bot.command()
@commands.is_owner()
async def rollback(ctx, index: typing.Optional[int]=-2):
    """Rolls back changes made during update to index"""
    if shogi_club.ready_to_update():
        if index in range(-len(shogi_club.log_games), len(shogi_club.log_games)):
            shogi_club.rollback_data(index)
            shogi_club.add_log(f"Rollback to: {index}.")
            await ctx.send(f"Changes rolled back to Log number {index}.")
        else:
            await ctx.send("Log index to rollback to out of range.")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Shows log history during update session
@bot.command()
@commands.is_owner()
async def logs(ctx):
    """Shows log history during update session"""
    log_string = ""
    if shogi_club.ready_to_update():
        for index, log_message in enumerate(shogi_club.log_comments):
            log_string += f"{index:>3}: {log_message}\n"
        await ctx.send("```Change Log:\n" + log_string + "```")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Pushes current scores to history
@bot.command()
@commands.is_owner()
async def push(ctx, date=str(datetime.now().date())):
    """Pushes current scores to history: date(opt. yyyy-mm-dd)"""
    if shogi_club.ready_to_update():
        shogi_club.append_player_data(date)
        shogi_club.add_log("Pushed to history")
        await ctx.send("Pushed data to player history.")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Adds new player
@bot.command()
@commands.is_owner()
async def add_player(ctx, full_name, elo: typing.Optional[int]=1100):
    """Add player: full_name, elo=1100"""
    if shogi_club.ready_to_update():
        if shogi_club.get_nick_name(full_name):
            await ctx.send("Player already exists.")
        else:
            nick_name = shogi_club.new_nick_name(full_name)
            shogi_club.add_new_player(nick_name, full_name, elo)
            shogi_club.add_log(f"New Player: {nick_name}")
            await ctx.send(f"Player {nick_name} added with {elo} ELO.")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Add games and update scores
@bot.command()
@commands.is_owner()
async def add(ctx, name1, name2, game_mode, result, comments, date=str(datetime.now().date())):
    """P1, P2, game_mode, W/L/D, comments, date(opt. ymd)"""
    if shogi_club.ready_to_update():
        nick1 = shogi_club.get_nick_name(name1)
        nick2 = shogi_club.get_nick_name(name2)
        if not (nick1 and nick2):
            if not nick1:
                await ctx.send(f"Player {name1} doesn't exist.")
            if not nick2:
                await ctx.send(f"Player {name2} doesn't exist.")
        else:
            update_results = shogi_club.add_game(nick1, nick2, game_mode, result, comments, date)
            shogi_club.add_log(f"Added game {name1}, {name2}")
            await ctx.send(f"Game mode: {game_mode}\n{nick1} {update_results[0]}: ELO Change: {update_results[2]}, New ELO: {update_results[4]}\n{nick2} {update_results[1]}: ELO Change: {update_results[3]}, New ELO: {update_results[5]}")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Reruns calculations
@bot.command()
@commands.is_owner()
async def rerun_calculations(ctx):
    """Reruns entire data calculations."""
    if shogi_club.ready_to_update():
        shogi_club.rerun_game_calculations()
        shogi_club.add_log("Rerun Calculations on Player Data")
        await ctx.send("Rerun Calculations on Player Data")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Clears Players to rerun calculations
@bot.command()
@commands.is_owner()
async def clear_players(ctx):
    """Clears players to rerun calculations."""
    if shogi_club.ready_to_update():
        shogi_club.clear_players()
        shogi_club.add_log("Cleared Player Data")
        await ctx.send("Cleared Player Data")
    else:
        await ctx.send("ShogiClub not currently in an update session.")


# In[ ]:


# Shows the rankings
@bot.command()
async def ranking(ctx, rank_by: Literal['elo', 'kd', 'rate', 'games'], n=10):
    """Ranking of top n players by ELO, K/D, win%, games played."""
    
    column_names = {"elo":"ELO", "games":"total", "kd":"kd", "rate":"win_rate"}
    pretty_names = {"elo":"ELO", "games":"# Played", "kd":"K/D", "rate":"% Won"}
    result = f"Rank:      Name:  {pretty_names[rank_by]:>8}:\n"
                      
    sorted_rankings = shogi_club.players.sort_values(by=column_names[rank_by], ascending=False)
    for i in range(min(n, len(shogi_club.players))):
        if rank_by == "kd":
            result = result + f"{i+1:>5} {sorted_rankings.iloc[i]['nick_name']:>10}   {sorted_rankings.iloc[i][column_names[rank_by]]:>8.2f}\n"
        elif rank_by == "games":
            result = result + f"{i+1:>5} {sorted_rankings.iloc[i]['nick_name']:>10}   {sorted_rankings.iloc[i][column_names[rank_by]]:>8}\n"
        else:
            result = result + f"{i+1:>5} {sorted_rankings.iloc[i]['nick_name']:>10}   {sorted_rankings.iloc[i][column_names[rank_by]]:>8.1f}\n"
    await ctx.send("```\n"+result+"```")


# In[ ]:


# Shows the members
@bot.command()
async def members(ctx, full_name="false"):
    """List of member names on data set"""
    
    if full_name == "false":
        result = f"Name:\n"
        sorted_rankings = shogi_club.players.sort_values(by="total", ascending=False)
        for i in range(len(shogi_club.players)):
            result = result + f"{sorted_rankings.iloc[i]['nick_name']:>10}\n"
    else:
        result = f"Names:\n"
        sorted_rankings = shogi_club.players.sort_values(by="total", ascending=False)
        for i in range(len(shogi_club.players)):
            result = result + f"{sorted_rankings.iloc[i]['full_name']:>22}\n"

    await ctx.send("```\n"+result+"```")


# In[ ]:


# Shows matchups
@bot.command()
async def matchup(ctx, name1, name2):
    """Probabilities on hypothetical matchups"""
    result = f"{'Matchup':^27}\n{name1:<12} v {name2:>12}\n"
    result = result + f"Win%: {100*shogi_club.expected(shogi_club.get_player_stat(name1, 'ELO'),shogi_club.get_player_stat(name2, 'ELO')):<6.1f}   {'Win%: ' + shogi_club.format_float(100*shogi_club.expected(shogi_club.get_player_stat(name2, 'ELO'), shogi_club.get_player_stat(name1, 'ELO'))):>12}\n"
    result = result + f"ELO: {shogi_club.get_player_stat(name1, 'ELO'):<7.1f}   {'ELO: ' + shogi_club.format_float(shogi_club.get_player_stat(name2, 'ELO')):>12}\n"
    win1, loss2 = shogi_club.new_elo(name1, name2, 1, 0)
    win2, loss1 = shogi_club.new_elo(name2, name1, 1, 0)
    result = result + f"Win∆: {win1:<6.1f}   {'Win∆: ' + shogi_club.format_float(win2):>12}\n"
    result = result + f"Loss∆: {loss1:<6.1f}  {'Loss∆: ' + shogi_club.format_float(loss2):>12}\n"
    await ctx.send("```\n"+result+"```")


# In[ ]:


# Shows history of games
@bot.command()
async def history(ctx, n=10):
    """List history of n games"""
    result_scores = {"W":"L", "L":"W", "D":"D"}
    result = f"#   {'Games:':<10}\n"
    for i in range(min(n,len(shogi_club.games))):
        row = shogi_club.games.iloc[len(shogi_club.games)-1-i]
        result = result + f"{len(shogi_club.games)-i:<3} {row['date']:<10} {row['name1']:>8} - {row['result']} {row['name2']:>8} - {result_scores[row['result']]}     {row['game_mode']}\n"

    await ctx.send("```\n"+result+"```")


# In[ ]:


# Shows specific game
@bot.command()
async def game(ctx, num=len(shogi_club.games)):
    """Show details on individual games"""
    row = shogi_club.games.iloc[min(max(1, num), len(shogi_club.games))-1]
    result_scores = {"W":"L", "L":"W", "D":"D"}
    
    result = f"{'Game #'+str(min(max(1, num), len(shogi_club.games))):<11}{row['date']:>17}\n{'Names:':<10}{row['name1']:>8}  {row['name2']:>8}\n"
    result = result + f"{'Result:':<10}{row['result']:>8}  {result_scores[row['result']]:>8}\n"
    result = result + f"{'Expected:':<10}{100*row['expectation']:>8.1f}  {100-100*row['expectation']:>8.1f}\n"
    result = result + f"{'ELO:':<10}{row['ELO1']:>8.1f}  {row['ELO2']:>8.1f}\n"
    result = result + f"{'∆ELO:':<10}{row['change_elo1']:>8.1f}  {row['change_elo2']:>8.1f}\n"
    result = result + f"Comments: {row['comments']}\n"
    await ctx.send("```\n"+result+"```")


# In[ ]:


# Shows profile of player
@bot.command()
async def profile(ctx, name):
    """Show details on players"""
    row = shogi_club.players[shogi_club.players["nick_name"] == name]
    
    result = f"{name} ({row['full_name'].values[0]})\n\n"
    result = result + f"{'Won: ' + str(row['win'].values[0]):<9} {'Lost: ' + str(row['loss'].values[0]):<9} {'Draw: ' + str(row['total'].values[0]-row['loss'].values[0]-row['win'].values[0]):<9} {'Total: ' + str(row['total'].values[0]):<9}\n\n"
    result = result + f"ELO:{row['ELO'].values[0]:>11.1f}\n"
    result = result + f"K/D: {row['kd'].values[0]:>10.2f}\n"
    result = result + f"Win%:{row['win_rate'].values[0]:>10.1f}\n"
    await ctx.send("```\n"+result+"```")


# In[ ]:


# Graphs changes in rankings
@bot.command()
async def graph(ctx, rank_by: Literal['elo', 'kd', 'rate', 'games'], n=5):
    """Ranking of top n players by ELO, K/D, win%, games played."""
    shogi_club.graph_players(rank_by, n)
    await ctx.send(file=discord.File('Shogi-Club-Discord-Bot/images/ranking.png'))
    

