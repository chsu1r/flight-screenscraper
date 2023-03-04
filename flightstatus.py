import requests as r
from bs4 import BeautifulSoup
import json
import csv
from time import sleep
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl

class Scraper(object):
    def __init__(self, pages=None):
        self.pages = pages
        if self.pages is None:
            self.pages = 299  # max for United on 2/25/2023
        self.data = []  # [[flight no, arrival time string, departure time string, origin airport, arrival airport]...]
    
    def gen_req_url(self, page_no):
        base = "https://united-airlines.flight-status.info"
        page_suffix = "page-" + str(page_no)
        return base + "/" + page_suffix
    
    def scrape(self):
        limit = self.pages
        for i in range(1, limit + 1):
            print("loading from " + self.gen_req_url(i))
            resp = r.get(self.gen_req_url(i))
            soup = BeautifulSoup(resp.content, "html.parser")
            tbody = soup.find("tbody")
            rows = tbody.find_all("tr")
            for row in rows[1:]:
                flight_no = row.find("h3").text.strip()
                times = row.find_all("td", class_="text-bold")
                departure_time, arrival_time = times[0].text, times[1].text
                locations = row.find_all("td", class_="hidden-xs")
                origin_airport = locations[0].text
                arrival_airport = locations[1].text
                self.data.append([flight_no, departure_time, arrival_time, origin_airport, arrival_airport])
            sleep(5)
        
    def write_to_csv(self):
        with open("flights.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.data)

class SouthwestParser(object):
    def __init__(self):
        path = "sw_routeInfo_1_1.json"
        self.nonstop_flights = {}
        with open(path) as json_file:
            data = json.load(json_file)

            for departure_airport in data.keys():
                if data[departure_airport]["country_code"] != "US":
                    continue
                nonstops = []
                connections = data[departure_airport]['routes_connected']
                arrivals = data[departure_airport]["routes_served"]
                for i in range(len(connections)):
                    if connections[i] == 'N':
                        nonstops.append(arrivals[i])
                if nonstops:
                    self.nonstop_flights[departure_airport] = nonstops
    
    def get_all_airports(self):
        airports = set(self.nonstop_flights.keys())
        for destination_set in self.nonstop_flights.values():
            for airport in destination_set:
                airports.add(airport)
        print("SW airports: ", len(airports))
        return airports

class UnitedParser(object):
    def __init__(self):
        path = "flights.csv"
        self.nonstop_flights = {}

        with open(path, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                if "United States" not in row[-1] or "United States" not in row[-2]:
                    continue
                departure_code = row[-2][1:4]
                arrival_code = row[-1][1:4]
                if departure_code not in self.nonstop_flights:
                    self.nonstop_flights[departure_code] = []
                self.nonstop_flights[departure_code].append(arrival_code)
        self.nonstop_flights = {a: list(set(self.nonstop_flights[a])) for a in self.nonstop_flights if self.nonstop_flights[a]}
    
    def get_all_airports(self):
        airports = set(self.nonstop_flights.keys())
        for destination_set in self.nonstop_flights.values():
            for airport in destination_set:
                airports.add(airport)
        print("United airports: ", len(airports))
        return airports

class Grapher(object):
    def __init__(self, parser):
        self.graph = nx.Graph()
        all_airports = set(parser.nonstop_flights.keys())
        self.graph.add_nodes_from(all_airports)

        self.graph.add_edges_from([(a, b) for a in parser.nonstop_flights for b in parser.nonstop_flights[a]])

    def draw(self):
        print("Drawing...")
        plt.figure(3,figsize=(30,30)) 
        d = dict(self.graph.degree)
        
        nx.draw(self.graph, font_size=8, with_labels=True, node_size=[v * 5 for v in d.values()])
        plt.show()
        plt.savefig("graph.png") 

    def plot_degree_dist(self, norm=False):
        n_nodes = self.graph.number_of_nodes()
        aux_y = nx.degree_histogram(self.graph)
        print(aux_y)
        aux_x = list(range(0,len(aux_y)))
            
        if norm:
            for i in range(len(aux_y)):
                aux_y[i] = aux_y[i]/n_nodes
        plt.figure(3,figsize=(10,5)) 
        plt.title('\nDistribution Of Node Linkages (United)')
        plt.xlabel('Degree\n')
        plt.ylabel('Percentage of Nodes')
        plt.bar(aux_x, aux_y)
        plt.savefig("degrees.png") 

def plot_betweenness_centrality(united_grapher, sw_grapher):
    LIMIT = 20
    united = sorted(nx.betweenness_centrality(united_grapher.graph).items(), key = lambda i:i[1], reverse=True)[:LIMIT]
    united_rank = [united[i][1] for i in range(LIMIT)]
    sw = sorted(nx.betweenness_centrality(sw_grapher.graph).items(), key = lambda i:i[1], reverse=True)[:LIMIT]
    sw_rank = [sw[i][1] for i in range(LIMIT)]

    plt.figure(3,figsize=(10,5)) 
    plt.title('Betweenness Centrality of Top ' + str(LIMIT) + ' Serviced Airports')
    plt.xlabel('Service Rank\n')
    plt.ylabel('Betweenness Centrality')
    plt.plot(list(range(LIMIT)), sw_rank, label="Southwest")
    plt.plot(list(range(LIMIT)), united_rank, label="United")
    plt.legend()
    plt.savefig("bc.png") 

def bfs(parser):
    starting_node = "DEN"
    visited = {airport: False for airport in parser.get_all_airports()}
    to_visit = [(starting_node, 1)]  # (airport, round)

    max_round = 0

    while len(to_visit) > 0:
        curr, rounds = to_visit.pop(0)
        visited[curr] = True
        neighbors = parser.nonstop_flights.get(curr, [])
        for neighbor in neighbors:
            if not visited[neighbor]:
                to_visit.append((neighbor, rounds + 1))
                if rounds + 1 > max_round:
                    max_round = rounds + 1
        # sorry i know there are more efficient ways to do this but im tired
        to_visit = sorted(to_visit, key = lambda i: i[1], reverse=False)

    return max_round

# parse from screenscraping the united flights website
# scraper = Scraper(pages=None)
# scraper.scrape()
# scraper.write_to_csv()

# parse from a json file i found on southwest's website
# parser = SouthwestParser()

# parse from a json file i wrote after scraping united
# parser = UnitedParser()

sw_parser = SouthwestParser()
united_parser = UnitedParser()
united_grapher = Grapher(united_parser)
sw_grapher = Grapher(sw_parser)

# united_grapher.draw()

# Betweenness centrality
# plot_betweenness_centrality(united_grapher, sw_grapher)


# Degree distribution
# united_grapher.plot_degree_dist(norm=True)

# BFS rounds
print("Southwest ", bfs(sw_parser))
print("United ", bfs(united_parser))