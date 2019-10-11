-- Sports Betting Project

/* Drop tables */
DROP TABLE nflgames;
DROP TABLE nflodds;

/* Create tables */
CREATE TABLE nflweeks (
	currentdate DATE,
	nfl_week INT
);

CREATE TABLE nflgames (
	gameid SERIAL PRIMARY KEY,
	commencetimelong TEXT, 
	commencetimeshort TEXT,
	nfl_week INT, 
	hometeam TEXT,
	awayteam TEXT
);

CREATE TABLE nflodds(
	nfloddsid SERIAL PRIMARY KEY,
	gameid INT,
	currentdate TEXT,
	currenttime TEXT,
	website TEXT,
	bet_type TEXT,
	home_odds DECIMAL,
	away_odds DECIMAL,
	home_points DECIMAL,
	away_points DECIMAL
);

CREATE TABLE player_projections(
	nfl_week INT,
	player TEXT,
	position TEXT,
	team TEXT,
	pass_att FLOAT,
	cmp FLOAT,
	pass_yds FLOAT,
	pass_tds FLOAT,
	ints FLOAT,
	rush_att FLOAT,
	rush_yds FLOAT,
	rush_tds FLOAT,
	rec FLOAT,
	rec_yds FLOAT,
	rec_tds FLOAT,
	sack FLOAT,
	int FLOAT,
	fr FLOAT,
	ff FLOAT,
	def_td FLOAT,
	safety FLOAT,
	pa FLOAT,
	yds_agn FLOAT,
	fg FLOAT,
	fga FLOAT,
	xpt FLOAT,
	fpts FLOAT
);

/* Example/test queries */

SELECT * FROM nflweeks;

SELECT * FROM nflodds ORDER BY gameid DESC, bet_type, website, currentdate DESC;
SELECT COUNT(*) FROM nflodds;
TRUNCATE TABLE nflodds; 
INSERT INTO nflodds (gameid, currentdate, currenttime, website, bet_type, home_odds, away_odds, home_points, away_points) 
VALUES (16, $$09/18/2019$$, $$11:16:44$$, $$GTbets$$, $$Moneyline$$, 1.5, 2.7, 0, 0)

SELECT * FROM nflgames WHERE nfl_week = 5 ORDER BY gameid;
TRUNCATE TABLE nflgames;
INSERT INTO nflgames (commencetimelong, commencetimeshort, nfl_week, hometeam, awayteam)
VALUES ('Monday, September 23, 2019 08:15:00', '09/23/2019', 3, 'Chicago Bears', 'Washington Redskins')

SELECT * FROM player_projections;
TRUNCATE TABLE player_projections;

-- Finding Duplicates
SELECT * FROM
    nflodds a,
    nflodds b
WHERE
    a.gameid = b.gameid
    AND a.currentdate = b.currentdate
	AND a.currenttime = b.currenttime
	AND a.website = b.website
	AND a.bet_type = b.bet_type;