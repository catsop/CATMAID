
/**
 AreaServerModel singleton class abstracts area persistence
 */
var AreaServerModel = new function()
{
    var areaTools = [];
    var areas = [];

    /**
     Push a new trace to the backend.
     */
    this.pushTrace = function(tool, area, path)
    {

    };

    /**
     Sync display properties.
     */
    this.pushProperties = function(area)
    {

    };

    this.registerTool = function(tool)
    {
        areaTools.push(tool);
    };

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
    };

    /**
     * Update the list of areas with respect to the current parameters of the given tool and return a
     * list of visible areas.
     */
    this.pullAreas = function(tool)
    {
        // for now, just return the areas.
        return areas;
    };

    /**
     * Add a new area. This pushes the new area onto the area list, and syncs it with the server.
     */
    this.addArea = function(area)
    {
        areas.push(area);
    };

};


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
    };

    this.setOpacity = function(op)
    {
        for (var idx = 0; idx < fabricObjects.length; ++i)
        {
            fabricObjects[idx].opacity = op;
        }
        AreaServerModel.pushProperties(self);
    };

    this.setColor = function(c)
    {
        for (var idx = 0; idx < fabricObjects.length; ++i)
        {
            fabricObjects[idx].setColor(c);
        }
        AreaServerModel.pushProperties(self);
    };

    this.getColor = function()
    {
        return self.color;
    };

    this.getObjects = function()
    {
      return fabricObjects;
    };

    this.setName = function(name)
    {
        self.name = name;
        AreaServerModel.pushProperties(self);
    };

    this.addObject = function(obj)
    {
        fabricObjects.push(obj);
    };

    this.updatePosition = function(screenPos, scale)
    {
        for (i = 0; i < fabricObjects.length; ++i)
        {
            obj = fabricObjects[i];
            xs = obj.stackLeft;
            ys = obj.stackTop;
            xc = (xs - screenPos.left) * scale;
            yc = (ys - screenPos.top) * scale;
            obj.scale(scale / obj.originalScale);
            obj.setLeft(xc);
            obj.setTop(yc);
        }
    };

}


/**
 AreaTraceTool class handles area tracing operations
 */

function AreaTool()
{
    this.prototype = new Navigator();
    this.toolname = "Area Tracing Tool";
    this.width = 10;
    this.currentArea = new Area("Dumb Area");
    // Replaced when register() is called
    this.stack = null;
    this.lastPos = null;

    var self = this;
    var actions = [];
    var areas = [this.currentArea];

    var proto_mouseCatcher = null;

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
            setupProtoControls();
            createCanvasLayer();
            return true;
        }
    }));

    this.onmousemove = function(e)
    {
        if (e.button == 0)
        {
            self.canvasLayer.canvas._onMouseMoveInDrawingMode(e);
            return true;
        }
    };

    this.onmousedown = function(e)
    {
        if (e.button == 1)
        {
            proto_onmousedown(e);
            return true;
        }
        else if(e.button == 0)
        {
            self.canvasLayer.canvas._onMouseDownInDrawingMode(e);
            return true;
        }

    };

    this.onmouseup = function(e) {
        if (e.button == 1)
        {
            proto_onmouseup(e);
            return true;
        }
        else if (e.button == 0)
        {
            self.canvasLayer.canvas._onMouseUpInDrawingMode(e);
            return true;
        }
    };

    this.registerFabricObject = function(obj)
    {
        screenPos = self.stack.screenPosition();
        x_s = screenPos.left;
        y_s = screenPos.top;
        scale = self.stack.scale;

        obj.originalScale = scale;

        x_o = obj.getLeft();
        y_o = obj.getTop();

        obj.stackLeft = x_o / scale + x_s;
        obj.stackTop = y_o / scale + y_s;

        self.currentArea.addObject(obj);
    };

    var setupProtoControls = function()
    {
        self.prototype.register( self.stack, "edit_button_area" );
        proto_mouseCatcher = self.prototype.mouseCatcher;
        proto_onmouseup = proto_mouseCatcher.onmouseup;
        proto_onmousedown = proto_mouseCatcher.onmousedown;
        proto_mouseCatcher.onmouseup = self.onmouseup;
        proto_mouseCatcher.onmousedown = self.onmousedown;
        proto_mouseCatcher.onmousemove = self.onmousemove;
    };

    var setupSubTools = function()
    {
        var box = createButtonsFromActions(
            actions,
            "toolbox_area",
            "area_");
        $( "#toolbox_area" ).replaceWith( box );
    };

    var createCanvasLayer = function()
    {
        self.canvasLayer = new AreaLayer( self.stack, self);
        var canvas = self.canvasLayer.canvas;

        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        canvas.freeDrawingBrush.width = self.width;
        canvas.isDrawingMode = true;

        canvas.on('path:created', function(e){
            if (self.currentArea)
            {
                self.registerFabricObject(e.path);
            }
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

        self.canvasLayer.view.onmousedown = self.onmousedown;
        self.canvasLayer.view.onmouseup = self.onmouseup;
    };

    var currentZ = function()
    {
        return self.stack.z * self.stack.resolution.z + self.stack.translation.z;
    };

    this.register = function(parentStack)
    {
        g_Area = self;

        self.stack = parentStack;

        $("#toolbox_area").show();

        $("#edit_button_area").switchClass("button", "button_active", 0);

        self.prototype.register( parentStack, "edit_button_area" );
        proto_mouseCatcher = self.prototype.mouseCatcher;

        setupSubTools();
        //createCanvasLayer();

        AreaServerModel.addArea(self.currentArea);
        AreaServerModel.registerTool(self);

    };

    this.unregister = function()
    {
        self.prototype.destroy( "edit_button_area" );
        return;
    };

    this.destroy = function()
    {
        $("#edit_button_area").switchClass("button_active", "button", 0);
        $("#toolbox_area").hide();
        return;
    };

    this.resize = function(height, width)
    {
        self.canvasLayer.resize(height, width);
    };

    this.cacheScreenParameters = function()
    {
        self.lastPos = self.stack.screenPosition();
        self.lastScale = self.stack.scale;
        self.lastZ = currentZ();
    };

    this.redraw = function() {

        if (self.lastPos)
        {
            self.cacheScreenParameters();

            for (i = 0; i < areas.length; ++i)
            {
                areas[i].updatePosition(self.stack.screenPosition(), self.stack.scale);
            }
        }
        else
        {
            self.cacheScreenParameters();
        }

        self.canvasLayer.canvas.renderAll();
    };

    this.setArea = function(area)
    {
        self.currentArea = area;
    };

    this.getArea = function()
    {
        return self.currentArea;
    };

    /**
     * This function should return true if there was any action
     * linked to the key code, or false otherwise.
     */
    /*this.handleKeyPress = function( e )
     {
     var keyAction = keyCodeToAction[e.keyCode];
     if (keyAction) {
     return keyAction.run(e);
     } else {
     return false;
     }
     }*/

    var keyCodeToAction = getKeyCodeToActionMap(actions);
}
