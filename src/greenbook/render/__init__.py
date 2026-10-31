import matplotlib

# Greenbook only writes PDF files. A GUI backend (Windows defaults to Tk) breaks when figures are
# made off the main thread, as in the web UI, so always use the file-only backend.
matplotlib.use("Agg")
