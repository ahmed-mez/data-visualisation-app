from config import LOG_DIR, LOG_FILE, ARTISTS, TAGS, TAGGED_ARTISTS
from wtforms import Form, TextField, SubmitField, SelectField
from flask import Flask, render_template, Response, request
from wtforms.validators import Required, ValidationError
from collections import Counter, OrderedDict
from bokeh.models import HoverTool
from bokeh.embed import components
from bokeh.plotting import figure
from numpy import pi
import pandas as pd
from os import path
import logging
import json


# Flask object
app = Flask(__name__)

# logging config
log_filename = path.join(LOG_DIR, LOG_FILE)
logging.basicConfig(filename=log_filename, level=logging.INFO)

# reading data from .dat files using pandas
artists = pd.read_csv(ARTISTS, usecols=[0, 1], sep="\t")
tags = pd.read_csv(TAGS, usecols=[0, 1], sep="\t", encoding="latin1")
tagged_artists = pd.read_csv(TAGGED_ARTISTS, sep="\t", usecols=[
                             1, 2],  dtype={"artistID": int, "tagID": int})

# mapping each artist name to its id
artists_mapping = artists.set_index("name").T.to_dict()

# mapping each tagID to its tagValue
tags_mapping = tags.set_index("tagID").T.to_dict()


class SearchForm(Form):
    """Class SearchForm, heritates from Form.
    Attributes:
        artist -- type: TextField
            the artist name, string
        submit -- type: SubmitField
            the submit field used to send form
    Methods:
        validate_artist
    """
    artist = TextField(None,
                       validators=[Required()],
                       id="artist_autocomplete",
                       render_kw={
                        "placeholder": "Type artist name e.g. Metallica",
                        "oninput": "this.setCustomValidity('')",
                        "oninvalid": "this.setCustomValidity('Please select \
                        an artist from the suggested options')"
                        })
    max_tags = SelectField("Maximum tags to show",
                           choices=[
                            ("10", "10 most used tags"),
                            ("15", "15 most used tags"),
                            ("20", "20 most used tags")
                           ])
    submit = SubmitField("Select")

    def validate_artist(self, field):
        """Check if the entered artist exist in the dataset.

        Raise: ValidationError
            if artist name is not string or if doesn't exist
        """
        if not isinstance(field.data, str):
            raise ValidationError('Artist name must be a string, got %s', type(field.data))
        if not field.data in artists_mapping.keys():
            raise ValidationError('Wrong artist name, got %s', field.data)


def get_tags_values_by_ids(tags_ids):
    """Get tags values by ids using the tags_mapping dictionary.

    Arguments:
        tags_ids -- type: [int]
            list of tags ids, list of integers

    Return:
        type: [str]
            list of corresponding tag values, list of strings
    """
    return [tags_mapping[tag_id]["tagValue"] for tag_id in tags_ids]


def center(l):
    """Center a sorted list.

    Arguments:
        l -- type: []
            list to be centered, list

    Return:
        type: []
            centered list, list
    """
    centered_list = []
    switch = True
    for element in l:
        if switch:
            # add element at right
            centered_list.append(element)
            switch = False
        else:
            # add element at left
            centered_list.insert(0, element)
            switch = True
    return centered_list


def create_graph(artist, tags_number=10):
    """Create a graph of tags used for a selected artist

    Arguments:
        artist -- type: str
            name of the selected artist, string

    Keyword Arguments:
        tags_number -- type: int (default 10)
            number of tags to be shown in the graph, integer

    Return:
        type: bokeh figure instance
    """
    # make sure tags_number is an integer
    try:
        tags_number = int(tags_number)
    except ValueError:
        tags_number = 10

    # get artist id using artists_mapping dictionary
    artist_id = artists_mapping[artist]["id"]

    # extract relative tags id for this artist using pandas
    artist_tags_ids_list = tagged_artists.loc[tagged_artists["artistID"] == artist_id, [
        "tagID"]].T.to_dict("split")["data"][0]

    # using Counter() data structure to count tags occurences
    count_tags = Counter(artist_tags_ids_list)
    ARTIST_TAGS_NUMBER = len(count_tags)

    if ARTIST_TAGS_NUMBER == 0:
        # return an empty graph if artist have zero tags
        logging.warning("no tags found for artist %s", artist)
        return None
    else:
        try:
            # exctract the most used tags for this artist
            NUMBER_TO_EXTRACT = min(tags_number, ARTIST_TAGS_NUMBER)
            most_used_tags = OrderedDict(count_tags.most_common(NUMBER_TO_EXTRACT))
            # get tags values by ids
            most_used_tags_values = get_tags_values_by_ids(list(most_used_tags.keys()))
            logging.info("got tags for artist %s", artist)
        except Exception:
            logging.error("cannot get tags for artist %s", artist)
            return None
        try:
            # define ranges
            MAX_RANGE = list(most_used_tags.values())[0]
            MIN_LIMIT = min(tags_number - 1, len(most_used_tags.values()) - 1)
            MIN_RANGE = list(most_used_tags.values())[MIN_LIMIT]

            # center tags values and counts and prepare axes
            x_axis = center(most_used_tags_values)
            y_axis = center(list(most_used_tags.values()))

            # plot the graph
            graph = figure(x_range=x_axis,
                           y_range=(max(0, MIN_RANGE - 2), MAX_RANGE + 2),
                           plot_width=800 + tags_number*5,  # adapt plot_width to tags_number
                           plot_height=500)
            graph.circle(x=x_axis, y=y_axis, size=20, color="navy", alpha=0.5)
            graph.xaxis.major_label_orientation = pi/4

            # gragh settings
            graph.background_fill_color = "#f5f5f5"
            graph.border_fill_color = "#fafafa"
            graph.grid.grid_line_color = "white"
            graph.xaxis.axis_label = "Tags"
            graph.yaxis.axis_label = 'Numbers of tags for {}'.format(artist)

            graph.add_tools(HoverTool(
                tooltips=[
                    ("tag", "@x"),
                    ("tag count", "@y")
                ]
            ))

            # toolbar settings
            graph.toolbar.logo = None
            graph.toolbar_location = None

            logging.info("graph created for artist %s", artist)
            return graph
        except Exception:
            logging.error("cannot create graph for artist %s", artist)
            raise


@app.route('/_autocomplete', methods=["GET"])
def autocomplete():
    """Autocomplete route used by jquery.
    """
    return Response(json.dumps(list(artists_mapping.keys())),
                    mimetype='application/json')


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        """Handle GET requests.
        show the form to select an artist name.
        """
        form = SearchForm(request.form)
        assert(isinstance(form, SearchForm))
        return render_template("index.html", form=form), 200
    if request.method == "POST":
        """Handle POST requests.
        get artist name from the request and create
        a corresponding graph of tags.
        """
        artist = request.form.get("artist")
        max_tags = request.form.get("max_tags")
        form = SearchForm(request.form)
        if form.validate():
            try:
                graph = create_graph(artist, tags_number=max_tags)
                if graph is None:
                    # artist has zero tags
                    error_msg = "artist has zero tags"
                    return render_template("index.html", form=form, error_msg=error_msg, artist=artist), 200
                # valid graph
                script, div = components(graph)
                return render_template("index.html", form=form, artist=artist, div=div, script=script), 200
            except Exception:
                error_msg = "cannot create graph"
                form = SearchForm(request.form)
                logging.error("error in handling form: %s", error_msg)
                return render_template("index.html", form=form, error_msg=error_msg), 500
        else:
            error_msg = "invalid artist name"
            form = SearchForm(request.form)
            logging.warning("invalid form: %s", error_msg)
            return render_template("index.html", form=form, error_msg=error_msg, artist=artist), 400


if __name__ == "__main__":
    app.run(host='0.0.0.0')
