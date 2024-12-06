from applications.view.system import register_system_bps
from applications.view.plugin import register_plugin_views
from applications.view.myview import bp as myview_bp

def init_bps(app):
    register_system_bps(app)
    register_plugin_views(app)
    app.register_blueprint(myview_bp)
