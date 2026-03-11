import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.lib.plugins import DefaultTranslation

from ckanext.link.views import link_checker


class LinkPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITranslation)

    # IConfigurer

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")

    # IBlueprint

    def get_blueprint(self):
        return [link_checker]
