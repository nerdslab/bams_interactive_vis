import numpy as np
import pandas as pd
from bokeh.layouts import column, row, gridplot
from bokeh.models import ColumnDataSource, CustomJS, Slider
from bokeh.plotting import figure, save, show
from bokeh.io import output_notebook, reset_output
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.models.widgets import Button
from bokeh.models.formatters import TickFormatter


def generate_visualization(keypoints, short_term_reps, long_term_reps, labels=None, time_steps=None, skip_every=1, 
                           edges=None, cage_locs=None):
    '''
    keypoints: np.array, shape=(sequence_length, num_points, 2)
    short_term_reps: dict, {reps: np.array(shape=(sequence_length, 2)), c: np.array(shape=(num_samples, sequence_length))}
    long_term_reps: dict, {reps: np.array(shape=(sequence_length, 2)), c: np.array(shape=(num_samples, sequence_length))}
    labels (optional): dict, {keypoints: str, short: str, long: str}. If included will be used to label the respective plots
    time_steps (optional): tuple, (start, end). The time steps to visualize. Default will show the whole sequence
    skip_every (optional): int. The number of time steps to skip when visualizing the keypoints (use if laggy / long sequences)
    edges (optional): np.array, shape=(num_edges, 2). The edges to visualize between keypoints. Each value should be a number (0, num_keypoints) 
                                            which corresponds to the index of the keypoint in the keypoints array
    cage_locs (optional): np.array, shape=(lines, 4). The cage edges to visualize in the plot. Each value should be a pixel location.
                                           Array should be formattes such that each row is a line and the columns are the x0, y0, x1, y1
    '''
    # Args
    COLOR_M1 = "blue"
    WIDTH = 640
    HEIGHT = 480

    if time_steps is None:
        time_steps = (0, keypoints.shape[0])
    # Extract and format the trajectory data
    n_points = keypoints.shape[1]
    n_time_steps = np.ceil((time_steps[1] - time_steps[0]) / skip_every).astype(int)

    # [seq_len, num_feats] -> [sequence_length, num_mice, num_keypoints, 2] 
    kps = keypoints[..., np.newaxis].transpose(0, 3, 1, 2)
    trajectory = kps[time_steps[0]:time_steps[1]:skip_every] 
    x = trajectory[:, :, :, 0].reshape(n_time_steps, -1)
    y = trajectory[:, :, :, 1].reshape(n_time_steps, -1)
    c = np.repeat(np.array([COLOR_M1]), n_points)

    # Create a DataFrame with time steps as columns
    df_points = pd.DataFrame(
        {"x": x.flatten(), "y": y.flatten(), "time_step": np.repeat(np.arange(n_time_steps), n_points),
        "c": np.tile(c, n_time_steps)}
    )

    df_edges = pd.DataFrame(
        {
            "x0": x[:, edges[:,0]].flatten(),
            "y0": y[:, edges[:,0]].flatten(),
            "x1": x[:, edges[:,1]].flatten(),
            "y1": y[:, edges[:,1]].flatten(),
            "time_step": np.repeat(np.arange(n_time_steps), len(edges)),
        }
    )

    source_points = ColumnDataSource(df_points[df_points["time_step"] == 0])
    source_lines = ColumnDataSource(df_edges[df_edges["time_step"] == 0])

    # cage
    if cage_locs is not None:
        cage_edges_x0, cage_edges_x1 = cage_locs[:, 0], cage_locs[:, 2]
        cage_edges_y0, cage_edges_y1 = cage_locs[:, 1], cage_locs[:, 3]

    # latent space
    long_term_emb_dict = long_term_reps['reps'][time_steps[0]:time_steps[1]:skip_every] 
    short_term_emb_dict = short_term_reps['reps'][time_steps[0]:time_steps[1]:skip_every] 

    start = time_steps[0]
    end = time_steps[1]
    long_z_trajectory_x = long_term_emb_dict[:, 0]
    long_z_trajectory_y = long_term_emb_dict[:, 1]
    short_z_trajectory_x = short_term_emb_dict[:, 0]
    short_z_trajectory_y = short_term_emb_dict[:, 1]
    long_z_trajectory_strain = np.zeros

    STRAIN_COLOR_1 = 'indigo'
    STRAIN_COLOR_2 = 'gold'

    df_long_term = pd.DataFrame({"x": long_z_trajectory_x, "y": long_z_trajectory_y, "c": long_term_reps['c'][time_steps[0]:time_steps[1]:skip_every]})
    source_long_term = ColumnDataSource(df_long_term)
    df_short_term = pd.DataFrame({"x": short_z_trajectory_x, "y": short_z_trajectory_y, "c": short_term_reps['c'][time_steps[0]:time_steps[1]:skip_every]})
    source_short_term = ColumnDataSource(df_short_term)

    df_l_trajectory = pd.DataFrame({"x": long_z_trajectory_x, "y": long_z_trajectory_y,
                                    "c": np.repeat("orchid", n_time_steps),
                                    "time_step": np.arange(n_time_steps)})
    source_l_trajectory = ColumnDataSource(df_l_trajectory)
    df_s_trajectory = pd.DataFrame({"x": short_z_trajectory_x, "y": short_z_trajectory_y,
                                    "c": np.repeat("yellow_green", n_time_steps),
                                    "time_step": np.arange(n_time_steps)})
    source_s_trajectory = ColumnDataSource(df_s_trajectory)


    output_notebook()

    # Create the scatter plot
    try:
        mouse_title = f"Extracted keypoints: {labels['keypoints']}"
    except:
        mouse_title = "Keypoints"
    plot_mice = figure(plot_width=3*WIDTH//4, plot_height=3*HEIGHT//4, x_range=(0, WIDTH), y_range=(0, HEIGHT), tools="", toolbar_sticky=False, title=mouse_title, output_backend="webgl")
    # configure the figure
    # remove the toolbar
    plot_mice.toolbar.logo = None
    plot_mice.toolbar_location = None
    # remove the x and y ticks
    plot_mice.xaxis.visible = False
    plot_mice.yaxis.visible = False
    # more things
    plot_mice.outline_line_color = "black"
    plot_mice.grid.grid_line_dash = [6, 4]
    plot_mice.title.text_font_size = "15px"
    plot_mice.title.text_font_style = "normal"
    # plot.outline_line_width = 1

    # Add the scatter plot
    plot_mice.scatter("x", "y", source=source_points, color="c")
    plot_mice.segment(x0="x0", y0="y0", x1="x1", y1="y1", source=source_lines, color='green')
    if cage_locs is not None:
        plot_mice.segment(x0=cage_edges_x0, y0=cage_edges_y0, x1=cage_edges_x1, y1=cage_edges_y1, color='black')

    # Add long-term latent
    try:
        long_title = f"Long-term embedding space: {labels['long']}"
    except:
        long_title = "Long-term embedding space"
    tools = "pan,box_zoom,reset"
    tools = ""
    plot_long_term = figure(plot_width=3*HEIGHT//4, plot_height=3*HEIGHT//4, toolbar_sticky=False, tools=tools, title=long_title, output_backend="webgl")
    plot_long_term.title.text_font_size = "15px"
    plot_long_term.scatter("x", "y", color="c", source=source_long_term, alpha=0.4)#, legend_group='label')
    plot_long_term.circle("x", "y", color="black", source=source_l_trajectory, nonselection_fill_alpha=0., nonselection_line_alpha=0.)
    plot_long_term.line("x", "y", color="black", source=source_l_trajectory, alpha=0.5)
    plot_long_term.xgrid.grid_line_color = None
    plot_long_term.ygrid.grid_line_color = None
    plot_long_term.toolbar.logo = None
    # plot_long_term.legend.title = "Mouse strain"
    plot_long_term.legend.padding = 4
    plot_long_term.legend.margin = 5
    plot_long_term.legend.label_standoff = 2
    plot_long_term.legend.spacing = 2
    plot_long_term.legend.border_line_color  = "black"
    plot_long_term.legend.background_fill_alpha = 0.8
    plot_long_term.legend.orientation = "horizontal"
    plot_long_term.toolbar_location = None
    plot_long_term.title.text_font_style = "normal"
    # Add short-term latent
    try:
        short_title = f"Short-term embedding space: {labels['short']}"
    except:
        short_title = "Short-term embedding space"
    plot_short_term = figure(plot_width=3*HEIGHT//4, plot_height=3*HEIGHT//4, toolbar_sticky=False, tools=tools, title=short_title, output_backend="webgl")
    plot_short_term.title.text_font_size = "15px"
    plot_short_term.scatter("x", "y", color="c", source=source_short_term, alpha=0.4)#, legend_group='label')
    plot_short_term.circle("x", "y", color="black", source=source_s_trajectory, nonselection_fill_alpha=0., nonselection_line_alpha=0.)
    plot_short_term.line("x", "y", color="black", source=source_s_trajectory, alpha=0.5)
    plot_short_term.xgrid.grid_line_color = None
    plot_short_term.ygrid.grid_line_color = None
    plot_short_term.toolbar.logo = None
    # plot_short_term.legend.title = "strain"
    plot_short_term.legend.padding = 4
    plot_short_term.legend.margin = 5
    plot_short_term.legend.label_standoff = 2
    plot_short_term.legend.spacing = 2
    plot_short_term.legend.border_line_color  = "black"
    plot_short_term.legend.background_fill_alpha = 0.8
    plot_short_term.legend.orientation = "horizontal"
    plot_short_term.toolbar_location = None
    plot_short_term.title.text_font_style = "normal"

    # Create the slider
    slider = Slider(start=0, end=n_time_steps - 1, value=0, step=1, title="Frame", width=200)

    # Create a play button
    play_button = Button(label="►", width=40, height=40)
    # Create a row with the play button and the slider
    controls = row(play_button, slider)

    # Convert the DataFrame to a dictionary and then to a JSON string
    df_json = df_points.to_json(orient="records")
    df_edges_json = df_edges.to_json(orient="records")

    # Define the JavaScript callback
    callback = CustomJS(
        args=dict(source=source_points, source_edges=source_lines, df_json=df_json, df_edges_json=df_edges_json,
                x_range=(0, n_time_steps), source_l_trajectory=source_l_trajectory, source_s_trajectory=source_s_trajectory),
        code="""
        const time_step = parseInt(cb_obj.value);
        const df = JSON.parse(df_json);
        const df_edges = JSON.parse(df_edges_json);
        const new_data = df.filter(row => row.time_step === time_step);
        const new_data_edges = df_edges.filter(row => row.time_step === time_step);

        let x = [];
        let y = [];
        let c = [];
        for (const row of new_data) {
            x.push(row.x);
            y.push(row.y);
            c.push(row.c);
        }
        
        let x0 = [];
        let x1 = [];
        let y0 = [];
        let y1 = [];
        for (const row of new_data_edges) {
            x0.push(row.x0);
            x1.push(row.x1);
            y0.push(row.y0);
            y1.push(row.y1);
        }

        x_range.start = time_step - 300;
        x_range.end = time_step;
        
        let visible_range = Array.from(new Array(100 + Math.min(time_step-100, 0)), (x, i) => i + Math.max(0, time_step-100));
        source_l_trajectory.selected.indices = visible_range;
        source_l_trajectory.change.emit();
        source_s_trajectory.selected.indices = visible_range;
        source_s_trajectory.change.emit();
        source.data = {x: x, y: y, c: c};
        source.change.emit();
        source_edges.data = {x0: x0, x1: x1, y0: y0, y1: y1};
        source_edges.change.emit();
    """,
    )

    # Add the callback to the slider
    slider.js_on_change("value", callback)

    play_callback = CustomJS(
        args=dict(slider=slider, source=source_points, df_json=df_json, play_button=play_button, n_time_steps=n_time_steps),
        code="""
        function update() {
            let time_step = slider.value + 10;
            if (time_step > n_time_steps) {
                time_step = 1;
            }
            slider.value = time_step;
        }

        if (play_button.label == "►") {
            play_button.label = "⏸";

            play_button.timer = setInterval(update, 11);
        } else {
            play_button.label = "►";
            if (play_button.timer) {
                clearInterval(play_button.timer);
            }
        }
    """,
    )

    # Add the callback to the play button
    play_button.js_on_click(play_callback)

    # Display the scatter plot and slider
    layout = row(column(plot_mice, controls), plot_long_term, plot_short_term)
    show(layout)