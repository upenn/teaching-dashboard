from st_aggrid.shared import JsCode


def add_highlight(javascript_test: str, fgcolor:str, bgcolor: str) -> JsCode:
    """
    Adds a highlight to a cell
    :param javascript_test: The javascript test to perform, e.g. params.value > 0
    :param fgcolor: The foreground color to use if the test passes, e.g. 'black'
    :param bgcolor: The background color to use if the test passes, e.g. 'green'
    """
    return JsCode("""
                function(params) {
                    if ("""
                  + javascript_test +
                  """) {
                        return {
                            'color': '""" + fgcolor + """',
                            'backgroundColor': '""" + bgcolor + """'
                        }
                    }
                };
                """)
 
def add_url(text_field: str, href_field: str) -> JsCode:
    """
    Adds a URL to a cell
    :param text_field: The text to display in the cell, or params.data[text_field]
    :param href_field: The URL to link to, or params.data[href_field]
    """
    return JsCode("""
            class UrlCellRenderer {
            init(params) {
                this.eGui = document.createElement('a');
                this.eGui.innerText = '""" + text_field + """';
                this.eGui.setAttribute('href', '""" + href_field + """');
                this.eGui.setAttribute('style', "text-decoration:none");
                this.eGui.setAttribute('target', "_blank");
            }
            getGui() {
                return this.eGui;
            }
            }
        """)