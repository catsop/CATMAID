/**
 * The Canvas layer that hosts the tracing data
 */


function AreaLayer( stack, tool )
{
    // define the x,y location and width and height of the
    // current field of view of the canvas in bitmap pixel
    var xindex, yindex, width, height;

    this.setOpacity = function( val )
    {
        self.view.style.opacity = val;
        opacity = val;
    }

    this.getOpacity = function()
    {
        return opacity;
    }

    this.redraw = function()
    {
      // hack to make the tool redraw the canvas
      self.canvas.renderAll();
      tool.redraw();
      return;
    }

    this.resize = function( width, height )
    {
        width = width;
        height = height;

        view.style.width = width + "px";
        view.style.height = height + "px";

        canvashtml.style.width = width + "px";
        canvashtml.style.height = height + "px";

        canvas.setWidth( width );
        canvas.setHeight( height );

        return;
    }

    this.show = function () {
        view.style.display = "block";
    };
    this.hide = function () {
        view.style.display = "none";
    };

    var self = this;

    // internal opacity variable
    var opacity = 50;

    var view = document.createElement("div");
    view.className = "canvasOverlay";
    view.id = "canvasOverlayId";
    view.style.zIndex = 5;
    view.style.opacity = 0.5;
    view.style.left = "0px";
    view.style.top = "0px";
    view.style.border = "solid red 4px";
    self.view = view;

    // XXX: add it here to DOM
    stack.getView().appendChild( view );

    var canvashtml = document.createElement("canvas");
    canvashtml.id = "areaCanvas";
    //canvashtml.style.border = "solid green 2px";
    self.view.appendChild( canvashtml );

    // CURSOR: "url(" + STATIC_URL_JS + "widgets/themes/kde/svg-circle.cur) 15 15, crosshair"
    var canvas = this.canvas = new fabric.Canvas('areaCanvas', {
      isDrawingMode: true
    });

    canvas.on({
      'mouse:down': function(fe) {
        if (view.onmousedown) { view.onmousedown(fe.e); }
      },
      'mouse:up': function(fe) {
        if (view.onmouseup) { view.onmouseup(fe.e); }
      }
    });

    /*var canvas = new fabric.Canvas( 'myCanvas' , {
        interactive: false,
        selection: false,
        isDrawingMode: false,
        defaultcursor: 'pointer',
        hoverCursor: 'crosshair'});*/

    //self.canvas = canvas;

    this.getHeight = function() {
        return height;
    }

    this.getWidth = function() {
        return width;
    }

    this.unregister = function()
    {
        //self.stack.getView().removeChild( view );
    };

}
