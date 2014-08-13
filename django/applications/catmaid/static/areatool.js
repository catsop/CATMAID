
function AreaTool()
{
  this.prototype = new Navigator();
  this.toolname = "Area Tracing Tool";
  var self = this;
  var actions = new Array();

  this.addAction = function ( action ) {
    actions.push( action );
  };

  this.getActions = function () {
    return actions;
  };

  this.addAction( new Action({
    helpText: "Area editting tool",
    buttonName: "editor",
    buttonID: "area_edit_button",
    run: function(e) {
      WindowMaker.show('area-editting-tool');
      return true;
    }
  }));

  var setupSubTools = function()
  {
    var box = createButtonsFromActions(
      actions,
      "toolbox_area",
      "area_");
    $( "#toolbox_area" ).replaceWith( box );
  }

  this.register = function(parentStack)
  {
    self.stack = parentStack;

    $("#toolbox_area").show();

    $("#edit_button_area").switchClass("button", "button_active", 0);
    setupSubTools();

    self.prototype.register( parentStack, "edit_button_area" );

    return;
  }

  this.unregister = function()
  {
    self.prototype.destroy( "edit_button_area" );
    return;
  }

  this.destroy = function()
  {
    $("#edit_button_area").switchClass("button", "button_active", 0);
    $("#toolbox_area").hide()
    return;
  }

  this.resize = function(height, width)
  {
    return;
  }

  this.redraw = function()
  {
    return;
  }

  /**
  * This function should return true if there was any action
  * linked to the key code, or false otherwise.
  */
  this.handleKeyPress = function( e )
  {
    var keyAction = keyCodeToAction[e.keyCode];
    if (keyAction) {
      return keyAction.run(e);
    } else {
      return false;
    }
  }

  var keyCodeToAction = getKeyCodeToActionMap(actions);
}
