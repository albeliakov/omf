from omf import geo, feeder
import json, os, shutil
import networkx as nx
from os.path import join as pJoin
from omf.feeder import _obToCol
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

def kMean(pathToOmdFile):
	'''
	Use kmeans algorithm for clustering points for omd representation.
	'''
	with open(pathToOmdFile) as inFile:
		tree = json.load(inFile)['tree']
	nxG = feeder.treeToNxGraph(tree)
	#Numpy array with nodeName, latitude, longitude
	numpyGraph = np.array([[node,
		float(nx.get_node_attributes(nxG, 'pos')[node][0]), float(nx.get_node_attributes(nxG, 'pos')[node][1])]
		for node in nx.get_node_attributes(nxG, 'pos')], dtype=object)
	plt.switch_backend('TKAgg')
	#plt.scatter(numpyGraph[:,1], numpyGraph[:,2], s=20, c='b')
	#plt.show()
	Kmean = KMeans(n_clusters=20)
	Kmean.fit(numpyGraph[:,1:3])
	#plt.scatter(Kmean.cluster_centers_[:,0], Kmean.cluster_centers_[:,1], s=50, c='r')
	#plt.show()
	centerNodes = Kmean.cluster_centers_
	labelsArray = Kmean.labels_
	#Group 
	clusterDict = {i: numpyGraph[np.where(Kmean.labels_ == i)] for i in range(Kmean.n_clusters)}
	#Go through each cluster in the cluster dict
	#Get the lat lon
	#Get the nodes edges
	#If the edges are in the same cluster, remove it
	#Else if the edge connects to another cluster, check if it exists, and if not add an edge from cluster to node that isn't in the cluster 
	newGraph = nx.Graph()
	for centerNode in clusterDict:
		currentClusterGroup = clusterDict[centerNode]
		newGraph.add_node('centroid'+str(centerNode),attr_dict={'type':'centroid',
			'pos': (centerNodes[centerNode][0], centerNodes[centerNode][1]),
			'clusterSize': np.ma.size(currentClusterGroup,axis=0), 'lineCount': 0})
	#print(node_positions)
	print(nx.number_of_edges(nxG))
	for centerNode in clusterDict:
		currentClusterGroup = clusterDict[centerNode]
		print(np.ma.size(currentClusterGroup,axis=0))
		nxG.add_node('centroid'+str(centerNode),attr_dict={'type':'centroid', 'pos': (centerNodes[centerNode][0], centerNodes[centerNode][1])})
		intraClusterLines = 0
		for i in currentClusterGroup:
			currentNode = i[0]
			neighbors = nx.neighbors(nxG, currentNode)
			#check if nodes are in same cluster
			for neighbor in neighbors:
				#print(nx.get_node_attributes(nxG, 'type')[neighbor])
				if nx.get_node_attributes(nxG, 'type')[neighbor] is 'centroid':
					#Add edge between centroids, updating value if neccessary
					if ('centroid'+str(centerNode), neighbor) not in nx.edges(newGraph):
						newGraph.add_edge('centroid'+str(centerNode), neighbor, attr_dict={'type': 'centroidConnector', 'lineCount': 1})
					else:
						#nx.edges(newGraph)[('centroid'+str(centerNode), neighbor)]
						newGraph['centroid'+str(centerNode)][neighbor]['lineCount'] += 1
						#nx.get_edge_attributes('centroid'+str(centerNode), neighbor)
					#newGraph.remove_edge(currentNode, neighbor)
					#nxG.remove_edge(currentNode, neighbor)
				elif neighbor not in currentClusterGroup[:,0]:
					nxG.add_edge('centroid'+str(centerNode), neighbor, attr_dict={'type': 'centroidConnector'})
					#newGraph.add_edge('centroid'+str(centerNode), neighbor)
					#pass
				else:
					#nxG.remove_edge(currentNode, neighbor)
					#intraClusterLines += 1
					newGraph.node['centroid'+str(centerNode)]['lineCount'] +=1
					#pass
			if currentNode in newGraph:
				newGraph.remove_node(currentNode)

	#print([edge for edge in nxG.edges.data() if edge in nx.get_edge_attributes(nxG, 'type')[edge] =='centroidConnector'])
	print(nx.get_edge_attributes(newGraph, 'lineCount'))
	print(nx.number_of_edges(newGraph))
	print(nx.edges(newGraph))
	print(nx.nodes(newGraph))
	print(nxG.number_of_nodes())
	node_positions = {node: nx.get_node_attributes(newGraph, 'pos')[node] for node in nx.get_node_attributes(newGraph, 'pos')}
	nx.draw_networkx(newGraph, pos=node_positions, nodelist=[node for node in nxG if node in nx.get_node_attributes(newGraph, 'pos')], with_labels=False, node_size=4, width=5, edge_color='blue')
	plt.scatter(Kmean.cluster_centers_[:,0], Kmean.cluster_centers_[:,1], s=50, c='r')
	plt.show()
	#print(nxG.nodes())

	#for i in centerNodes:
		#nxG.add_node('center', attr_dict={'type':'center'})
		#print(nx.get_node_attributes(nxG,'center'))
		#print float(i[1])
if __name__ == '__main__':
	kMean('../../static/publicFeeders/Olin Barre LatLon.omd')