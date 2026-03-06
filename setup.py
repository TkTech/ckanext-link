from setuptools import setup

setup(
    message_extractors={
        "ckanext": [
            ("**.py", "python", None),
            ("**.html", "jinja2", None),
        ],
    },
)
