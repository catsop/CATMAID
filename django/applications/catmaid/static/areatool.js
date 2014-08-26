
/**
AreaServerModel singleton class abstracts area persistence
*/
var AreaServerModel = new function(stack)
{
  var areaTools = [];
  self.stack = stack;

  /**
  Push a new trace to the backend.
  */
  this.pushTrace = function(tool, area, path)
  {
    return;
  }

  /**
  Sync display properties.
  */
  this.pushProperties = function(area)
  {
    return;
  }

  this.registerTool = function(tool)
  {
    areaTools.push(tool);
  }

  this.deregisterTool = function(tool)
  {
    // Remove the tool from the areaTools array.
    for (var idx = 0; idx < areaTools.length; ++i)
    {
      if( areaTools[idx] === tool)
      {
        areaTools.splice(idx, 1);
        return;
      }
    }
  }

  this.pullAreas = function()
  {
    // Use self.stack to retrieve all visible areas.
    return;
  }

}


/**
Area class maintains geometric information
*/
function Area(name)
{
  this.color = 'rgb(255,0,0)';
  this.opacity = 1;
  this.name = name;

  var self = this;

  var fabricObjects = [];

  this.transform = function(t)
  {
    for (var idx = 0; idx < fabricObjects.length; ++i)
    {
      fabricObjects[idx].transformMatrix(t);
    }
  }

  this.setOpacity = function(op)
  {
    for (var idx = 0; idx < fabricObjects.length; ++i)
    {
      fabricObjects[idx].opacity = op;
    }
    AreaServerModel.pushProperties(self);
  }

  this.setColor = function(c)
  {
    for (var idx = 0; idx < fabricObjects.length; ++i)
    {
      fabricObjects[idx].setColor(c);
    }
    AreaServerModel.pushProperties(self);
  }

  this.getColor = function()
  {
    return self.color;
  }

  this.setName = function(name)
  {
    self.name = name;
    AreaServerModel.pushProperties(self);
  }

  this.addObject = function(obj)
  {
    fabricObjects.push(obj);
  }

}

/**
AreaTool class handles area tracing operations
*/
function AreaTool()
{
  this.prototype = new Navigator();
  this.toolname = "Area Tracing Tool";
  var area = null;
  var width = 10;

  var self = this;
  var actions = new Array();

  this.addAction = function ( action ) {
    actions.push( action );
  };

  this.getActions = function () {
    return actions;
  };

  this.addAction = new Action({
    helpText: "Area editting tool",
    buttonName: "editor",
    buttonID: "area_edit_button",
    run: function(e) {
      WindowMaker.show('area-editting-tool');
      return true;
    }
  });

  this.getWidth = function()
  {
    return width;
  }

  this.setWidth = function( w )
  {
    width = w;
    self.canvas.freeDrawingBrush.width = w;
  }

  this.setActiveArea = function(a)
  {
    area = a;
  }

  this.getActiveArea = function()
  {
    return area;
  }

  var setupSubTools = function()
  {
    var box = createButtonsFromActions(
      actions,
      "toolbox_area",
      "area_");
    $( "#toolbox_area" ).replaceWith( box );
  }

  var createCanvasLayer = function()
  {
    self.canvasLayer = new AreaLayer( self.stack, self);
    var canvas = self.canvasLayer.canvas;

    canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
    canvas.freeDrawingBrush.width = width;
    canvas.isDrawingMode = true;

    canvas.on('path:created', function(e){
      /*logArray = [];
      for (i = 0; i < e.path.path.length; ++i)
      {
        logArray.push(e.path.path[i][1]);
        logArray.push(e.path.path[i][2]);
      }
      console.log(logArray);*/
      console.log(e);
    });

    /*self.canvasLayer.view.onmousedown = function(e){
      return true
    };

    self.canvasLayer.view.onmouseup = function(e){
      return true
    };*/

    //canvas.interactive = true;

    self.stack.addLayer("AreaLayer", self.canvasLayer);
    self.stack.resize();
  }

  this.register = function(parentStack)
  {
    self.stack = parentStack;

    $("#toolbox_area").show();

    $("#edit_button_area").switchClass("button", "button_active", 0);

    setupSubTools();
    createCanvasLayer();

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
    $("#edit_button_area").switchClass("button_active", "button", 0);
    $("#toolbox_area").hide()
    return;
  }

  this.resize = function(height, width)
  {
    self.canvasLayer.resize(height, width);
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
