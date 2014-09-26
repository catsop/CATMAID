
/**
 AreaServerModel singleton class abstracts area persistence
 */
var AreaServerModel = new function()
{
    var areaTools = [];
    var areas = [];
    var django_url = '/sopnet/';

    /**
     Push a new trace (ie, fabricjs object) to the backend.
     */
    this.pushTrace = function(tool, area, object_container)
    {
        var x = [];
        var y = [];
        var pts = [];
        var obj = object_container.obj;
        var stack = tool.stack;
        var project = stack.getProject();
        var view_top = stack.screenPosition().top;
        var view_left = stack.screenPosition().left;
        var scale = stack.scale;
        var url = '/user_slice';
        var bound_rect = obj.getBoundingRect();
        var o_left = (bound_rect.left + (tool.width / 2.0)) / scale + view_left;
        var o_top = (bound_rect.top + (tool.width / 2.0)) / scale + view_top;
        var r = tool.width / (2.0 * scale);

        /*console.log('o_left: ' + o_left + ', o_top: ' + o_top);
        console.log('o_left_c: ' + obj.left + ', o_top_c: ' + obj.top);*/


        for (var i = 0; i < obj.path.length; ++i)
        {
            x.push(obj.path[i][1] / scale);
            y.push(obj.path[i][2] / scale);
            pts.push({x: obj.path[i][1], y: obj.path[i][2]});
        }

        var data = {'r' : r, //r, x, y in stack coordinates
            'x' : x,
            'y' : y,
            'section' : stack.z,
            'id' : object_container.id,
            'assembly_id' : area.assemblyId,
            'left': o_left,
            'top': o_top,
            'scale' : scale,
            'view_left': view_left,
            'view_top' : view_top
        };

        $.ajax({
            "dataType": 'json',
            "type": 'POST',
            "cache": false,
            "url": django_url + project.id + '/stack/' + stack.id + url,
            "data": data,
            "success": tool.pushCallback
        });
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
 Area class maintains geometric information for a given Assembly.
 */
function Area(name, assemblyId)
{
    this.color = 'rgb(255,0,0)';
    this.opacity = 1;
    this.name = name;
    this.assemblyId = assemblyId;

    var self = this;

    var fabricObjects = [];
    var objectTable = {};

    this.transform = function(t)
    {
        for (var idx = 0; idx < fabricObjects.length; ++i)
        {
            fabricObjects[idx].obj.transformMatrix(t);
        }
    };

    this.setOpacity = function(op)
    {
        for (var idx = 0; idx < fabricObjects.length; ++i)
        {
            fabricObjects[idx].obj.opacity = op;
        }
        AreaServerModel.pushProperties(self);
    };

    this.setColor = function(c)
    {
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            fabricObjects[idx].obj.setColor(c);
        }
        AreaServerModel.pushProperties(self);
    };

    this.getColor = function()
    {
        return self.color;
    };

    this.getObjects = function()
    {
        var objects = [];
        for (var idx = 0; idx < fabricObjects.length; ++idx)
        {
            objects.push(fabricObjects[idx].obj)
        }
        return objects;
    };

    this.setName = function(name)
    {
        self.name = name;
        AreaServerModel.pushProperties(self);
    };

    this.addObjectContainer = function(objectContainer)
    {
        var key = objectContainer.id;
        fabricObjects.push(objectContainer);
        objectTable[key] = objectContainer;
    };

    this.removeObject = function(key)
    {
        if (objectTable.hasOwnProperty(key))
        {
            var objectContainer = objectTable[key];
            var idx = fabricObjects.indexOf(objectContainer);
            fabricObjects.splice(idx, 1);
            delete objectTable[key];

            return objectContainer.obj;
        }
        else
        {
            return null;
        }
    };

    this.updatePosition = function(screenPos, scale)
    {
        for (var i = 0; i < fabricObjects.length; ++i)
        {
            var c = fabricObjects[i];
            var obj = c.obj;
            var xs = c.stackLeft;
            var ys = c.stackTop;
            var xc = (xs - screenPos.left) * scale;
            var yc = (ys - screenPos.top) * scale;

            obj.scale(scale / c.originalScale);
            obj.setLeft(xc);
            obj.setTop(yc);
        }
    };

}


function FabricObjectContainer(obj, scale, screenPos, id)
{
    var self = this;

    var x_o = obj.getLeft();
    var y_o = obj.getTop();

    var x_s = screenPos.left;
    var y_s = screenPos.top;

    this.obj = obj;
    this.stackLeft = x_o / scale + x_s;
    this.stackTop = y_o / scale + y_s;
    this.originalScale = scale;
    this.id = id;

}

/**
 AreaTraceTool class handles area tracing operations
 */
function AreaTool()
{
    this.prototype = new Navigator();
    this.toolname = "Area Tracing Tool";
    this.width = 10;
    this.currentArea = new Area("Dumb Area", 1);
    // Replaced when register() is called
    this.stack = null;
    this.lastPos = null;

    var self = this;
    var actions = [];
    var areas = [this.currentArea];
    var nextId = 0;

    var proto_mouseCatcher = null;

    var areaById = function(id)
    {
        for (var idx = 0; idx < areas.length; ++idx)
        {
            if (areas[idx].assemblyId == id)
            {
                return areas[idx];
            }
        }
        return null;
    };

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

    this.getArea = function(areaIdentifier)
    {
        var areaType = typeof areaIdentifier;

        if (areaType == 'undefined')
        {
            area = self.currentArea;
        }
        else if(areaType == 'object')
        {
            area = areaIdentifier;
        }
        else if (areaType == 'number')
        {
            area = areaById(areaIdentifier);
        }
        else
        {
            console.log('Unexpected area type');
        }

        return area;
    };

    this.registerDeserializedFabricObject = function(obj, areaIn, id, scaleIn,
                                                     screenRelativePositionIn)
    {
        var area = self.getArea(areaIn);
        var scale = 1.0;
        var screenRelativePosition = null;

        obj.setOriginX('center');
        obj.setOriginY('center');

        if (typeof scaleIn != 'undefined')
        {
            scale = scaleIn;
        }

        if (typeof screenRelativePositionIn == 'undefined')
        {
            screenRelativePosition = {left: 0, top: 0};
        }
        else
        {
            screenRelativePosition = screenRelativePositionIn;
        }

        var objectContainer = new FabricObjectContainer(obj, scale, screenRelativePosition, id);
        area.addObjectContainer(objectContainer);

        area.updatePosition(self.stack.screenPosition(), self.stack.scale);

        self.canvasLayer.canvas.renderAll();

        return objectContainer;
    };

    /**
     * Register a fabric.js Object to an Area
     *
     * @param obj the fabric.js object to register
     * @param areaIn the area identifier, one of:
     *        undefined - use the currentArea of this tool
     *        object - use this Area object
     *        number - use the Area with this assembly id
     */
    this.registerFreshFabricObject = function(obj, areaIn)
    {
        var area = self.getArea(areaIn);
        var objectContainer = new FabricObjectContainer(obj, self.stack.scale,
            self.stack.screenPosition(), nextId++);

        area.addObjectContainer(objectContainer);

        AreaServerModel.pushTrace(self, self.currentArea, objectContainer);
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
                self.registerFreshFabricObject(e.path);
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
        var proto_mouseCatcher = self.prototype.mouseCatcher;

        setupSubTools();
        //createCanvasLayer();

        AreaServerModel.addArea(self.currentArea);
        AreaServerModel.registerTool(self);

    };

    this.unregister = function()
    {
        self.prototype.destroy( "edit_button_area" );
    };

    this.destroy = function()
    {
        $("#edit_button_area").switchClass("button_active", "button", 0);
        $("#toolbox_area").hide();
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

    this.pushCallback = function(data)
    {
        console.log(data);
        if (data.hasOwnProperty('djerror'))
        {
            console.log(data.djerror);
        }
        else
        {
            var svgCall = function(objects, options)
            {
                var obj = fabric.util.groupSVGElements(objects, options);
                var area = self.getArea(data.assembly_id);

                obj.setColor(data.view_props.color);
                obj.setOpacity(data.view_props.color);

                self.registerDeserializedFabricObject(obj, area, data.id);
                self.canvasLayer.canvas.add(obj);

                area.updatePosition(self.stack.screenPosition(), self.stack.scale);

                for (var idx = 0; idx < data.replace_ids.length; ++idx)
                {
                    var rmObj = area.removeObject(data.replace_ids[idx]);
                    self.canvasLayer.canvas.remove(rmObj);
                }
            };

            fabric.loadSVGFromString(data.svg, svgCall);

            // Somehow, using either loadSVGFromURL or reading the svg from a url and using
            // loadSVGFromString causes fabricjs to ignore holes.

            /*
                        var loadSVG = function(ajaxData)
                        {
                            fabric.loadSVGFromString(ajaxData, svgCall);
                            console.log('via http:', ajaxData);
                            console.log('via post:', data.svg);
                        };

            var sliceUrl = '/sopnet/' + self.stack.getProject().id + '/stack/' + self.stack.id +
                '/polygon_slice/' + data.id + '.svg';
            fabric.loadSVGFromURL(sliceUrl, svgCall);

            $.ajax({
                "type": 'GET',
                "cache": true,
                "url": sliceUrl,
                "success": loadSVG
            });
*/

        }

    };

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
    };

    var keyCodeToAction = getKeyCodeToActionMap(actions);
}
