# shard/views.py
import pandas as pd
import networkx as nx
from pyvis.network import Network
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from .forms import UploadFileForm
import os
import pygwalker as pyg


def index(request):
    if request.method == "POST" and request.FILES["csv_file"]:
        csv_file = request.FILES["csv_file"]
        fs = FileSystemStorage()
        filename = fs.save(csv_file.name, csv_file)
        file_path = fs.path(filename)

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return HttpResponse(f"Failed to read CSV file: {e}", status=400)

        # Preview the dataframe
        context = {
            "columns": df.columns,
            "dataframe_preview": df.head().to_html(),
            "csv_file_path": filename
        }
        return render(request, "visualizer/select_columns.html", context)

    return render(request, "visualizer/index.html")


def visualize(request):
    if request.method == "POST":
        file_path = request.POST.get("csv_file_path")
        source_col = request.POST.get("source_col")
        target_col = request.POST.get("target_col")

        if not all([file_path, source_col, target_col]):
            return HttpResponse("Missing data for visualization", status=400)

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return HttpResponse(f"Failed to read CSV file: {e}", status=400)

        # Create graph from dataframe
        G = create_graph_from_df(df, source_col, target_col)

        # Validate and setup PyVis network
        try:
            validate_nodes(G)
        except Exception as e:
            return HttpResponse(f"Node validation failed: {e}", status=400)

        net = setup_pyvis_network(G)

        # Generate the PyVis visualization and render the HTML
        net_html = net.generate_html()
        pyg_html = pyg.walk(df, return_html=True, hideDataSourceConfig=False)

        return render(request, "visualizer/visualize.html", {"net_html": net_html, "pyg_html": pyg_html})

    return redirect("index")


def create_graph_from_df(df, source_col, target_col):
    df[source_col] = df[source_col].fillna("")
    df[target_col] = df[target_col].fillna("")

    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row[source_col], row[target_col])
    return G


def validate_nodes(G):
    for node in G.nodes:
        if not isinstance(node, (str, int)):
            raise ValueError(f"Node {node} has an invalid identifier type.")


def setup_pyvis_network(G):
    net = Network(height="750px", width="100%", directed=False, notebook=False)
    pos = nx.spring_layout(G, seed=42)
    for node, (x, y) in pos.items():
        net.add_node(node, x=x, y=y)
    for edge in G.edges():
        net.add_edge(*edge)
    return net
