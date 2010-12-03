/**
 * request.js
 *
 * requirements:
 *	 tools.js
 *
 */

/**
 */

/**
 * Implements a cross browser HTTPrequest-FIFO-queue as `singleton module'
 */
var requestQueue = function()
{
	var self = this;
	var queue = new Array();		//!< queue of waiting requests
	var xmlHttp;
	if ( typeof XMLHttpRequest != 'undefined' )
	{
		xmlHttp = new XMLHttpRequest();
	}
	else
	{
		try { xmlHttp = new ActiveXObject( "Msxml2.XMLHTTP" ); }
		catch( e )
		{
			try { xmlHttp = new ActiveXObject( "Microsoft.XMLHTTP" ); }
			catch( e ){ xmlHttp = null; }
		}
	}
	
	alert( xmlHttp );
	
	var encodeArray = function( a, p )
	{
		var q = "";
		for ( var i = 0; i < a.length; ++i )
		{
			var r = p + "[" + i + "]";
			
			switch ( typeof a[ i ] )
			{
			case "undefined":
				break;
			case "function":
			case "object":
				if ( a[ i ].constructor == Array && a[ i ].length > 0 )
					q += encodeArray( a[ i ], r ) + "&";
				else
					q += encodeObject( a[ i ], r ) + "&";
				break;
			default:
				q += r + "=" + encodeURIComponent( a[ i ] ) + "&";
				break;
			}
		}
		q = q.replace( /\&$/, "" );
		
		return q;
	}
	
	var encodeObject = function( o, p )
	{
		var q = "";
		for ( var k in o )
		{
			var r;
			if ( p )
				r = p + "[" + k + "]";
			else
				r = k;
			
			switch ( typeof o[ k ] )
			{
			case "undefined":
				break;
			case "function":
			case "object":
				if ( o[ k ].constructor == Array && o[ k ].length > 0 )
					q += encodeArray( o[ k ], r ) + "&";
				else
					q += encodeObject( o[ k ], r ) + "&";
				break;
			default:
				q += r + "=" + encodeURIComponent( o[ k ] ) + "&";
				break;
			}
		}
		q = q.replace( /\&$/, "" );
		
		return q;
	}
	
	var send = function()
	{
		xmlHttp.open(
			queue[ 0 ].method,
			queue[ 0 ].request,
			true );
		if ( queue[ 0 ].method == "POST" )
		{
			xmlHttp.setRequestHeader( "Content-type", "application/x-www-form-urlencoded" );
			xmlHttp.setRequestHeader( "Content-length", queue[ 0 ].data.length );
			xmlHttp.setRequestHeader( "Connection", "close" );
		}
		xmlHttp.onreadystatechange = callback;
		xmlHttp.send( queue[ 0 ].data );
		
		return;
	}
	
	var callback = function()
	{
		if ( xmlHttp.readyState == 4 )
		{
			queue[ 0 ].callback( xmlHttp.status, xmlHttp.responseText, xmlHttp.responseXML );
			queue.shift();
			if ( queue.length > 0 )
				send();
		}
		return;
	}
	
	return {
		/**
		 * Returns if there is some request pending or not.
		 */
		busy : function(){ return ( queue.length > 0 ); },
		
		/**
		 * Registers a request including a callback to the queue for waiting or
		 * starts it imediately.
		 */
		register : function(
				r,		//!< string  request
				m,		//!< string  method		"GET" or "POST"
				d,		//!< object  data		object with key=>value
				c,		//!< funtion callback
				id		//!< string  id
		)
		{
			switch( m )
			{
			case "POST":
				queue.push(
					{
						request : r,
						method : m,
						data : encodeObject( d ),
						callback : c,
						id : id
					}
				);
				break;
			default:
				queue.push(
					{
						request : r + "?" + encodeObject( d ),
						method : m,
						data : null,
						callback : c,
						id : id
					}
				);
			}
			if ( queue.length == 1 )
			{
				send();
			}
			return;
		},
	
		/**
		 * Registers a request including a callback to the queue for waiting or
		 * starts it imediately.  In case the requests id exists in the queue
		 * already, the existing instance will be removed assuming that it is
		 * outdated.
		 */
		replace : function(
				r,		//!< string  request
				m,		//!< string  method		"GET" or "POST"
				d,		//!< object  data		object with key=>value
				c,		//!< funtion callback
				id		//!< string  id
		)
		{
			for ( var i = 1; i < queue.length; ++i )
			{
				if ( queue[ i ].id == id )
				{
					queue.splice( i, 1 );
					statusBar.replaceLast( "replacing request ", + r );				
				}
			}
			this.register( r, m, d, c, id );
			statusBar.replaceLast( "queue.length = " + queue.length );
			return;
		}
	};
	
}();

