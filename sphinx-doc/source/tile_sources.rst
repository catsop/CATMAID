Tile Source Conventions
=======================

CATMAID does not serve image data itself. Instead, it stores a few critical
pieces of information about the image volume and specifies a set of conventions
for retrieving image data from a separate image volume host. These
conventions are `tile source types`, which define parameters and URL formats
both the CATMAID backend and frontend can use to access image data for
rendering and analysis.

This document provides information on the type source types specified by
CATMAID, the parameters which they use to retrieve image data, how this is
stored in the CATMAID backend, and how to create a new tile source type in the
CATMAID backend and frontend.

Tile Source Parameters
----------------------

Each tile source type uses a subset of the following parameters to determine
its source regardless of the specific tiles being retrieved. Though specific
APIs may use different names for these parameters, the names provided here are
used for consistency in defining tile source types below:

``sourceBaseURL`` (string)
   This defines a base URL for the source server and volume, including trailing
   slash.

``dimension`` (integer array [x, y, z])
   Dimension of the image volume in pixels at its original scale level.

``resolution`` (double array [x, y, z])
   Resolution of the image volume in nanometers at its original scale level.

``numZoomLevels`` (integer)
   The number of zoom levels (downsampling octaves) which the source supports.

``fileExtension`` (string)
   Filename extension for image tiles served by the source.

``tileWidth`` (integer)

``tileHeight`` (integer)
   Dimensions of image tiles in pixels. For pre-tiled sources, this should be
   the dimensions of the source tiles, while for dynamic sources this should be
   the preferred dimension for retrieval and rendering.

``orientation`` (integer|string)
   Orientation of the stack relation to project space. Semantically this value
   is either "XY", "XZ", "ZY", but is usually passed as an integer in {0, 1, 2}
   enumerating these, respectively.

   Currently only DVID tile source types (6, 8) must know orientation directly.
   Other tile source types encode orientation in the ``sourceBaseURL``.

``tileSourceType`` (integer)
   A integer enumerating the types of tile sources listed below.

Tile Parameters
---------------

Tile sources may additionally make use of a subset of the following
parameters when determining how to retrieve specific tile requests:

``row`` (integer)
   The row of the tile in the image grid for this z-slice, e.g., the floor of
   the tile y origin divided by ``tileHeight``.

``col`` (integer)
   The column of the tile in the image grid for this z-slice, e.g., the floor of
   the tile x origin divided by ``tileWidth``.

``zoomLevel`` (integer)
   The zoom level of tiles to retrieve. Zoom level 0 is the original scale,
   zoom level 1 is the first downsampled octave, etc.

``pixelPosition`` (integer array [x, y, z])
   The *stack space* position in pixels of a location in the plane of the tile.
   Usually this position is shared for many tile requests, e.g., the center of
   a stack viewer, and is used only to generate a path using the ``z`` location
   in the stack.

Tile Source Types
-----------------

Tile source types are listed by the enumeration integer ID referenced by
``tileSourceType``:

1. File-based image stack
*************************

   URL format::

    <sourceBaseUrl><pixelPosition.z>/<row>_<col>_<zoomLevel>.<fileExtension>

2. Request query-based image stack
**********************************

   URL format::

    <sourceBaseURL>?x=<col * tileWidth>
                   &y=<row * tileHeight>
                   &z=<pixelPosition.z>
                   &width=<tileWidth>
                   &height=<tileHeight>
                   &scale=<2^-zoomLevel>
                   &row=y
                   &col=x

3. HDF5 via CATMAID backend
***************************

   This is the only tile source type which the CATMAID backend serves directly.
   Django retrieves tile requests from an image volume stored in an HDF5 file.
   This is a convenience source intended for quick exploration of small volumes
   only and does not scale to large volumes or many users.

   As an exceptional source, this uses the following tile source parameters
   that should not be used by any other source:

   ``catmaidURL`` (string)
      Base URL of the CATMAID instance serving the volume, including trailing
      slash.

   ``projectId`` (integer)
      ID of the CATMAID project.

   ``stackId`` (integer)
      ID of the CATMAID stack.

   URL format::

    <catmaidURL><projectId>/stack/<stackID>/tile?x=<col * tileWidth>
                                                &y=<row * tileHeight>
                                                &z=<pixelPosition.z>
                                                &width=<tileWidth>
                                                &height=<tileHeight>
                                                &scale=<2^-zoomLevel>
                                                &row=y
                                                &col=x
                                                &file_extension=<fileExtension>
                                                &basename=<sourceBaseURL>
                                                &type=all

4. File-based image stack with zoom level directories
*****************************************************

   A variation on tile source type 1 where the zoom level is also a directory.

   URL format::

    <sourceBaseUrl><pixelPosition.z>/<zoomLevel>/<row>_<col>.<fileExtension>

5. Directory-based image stack
******************************

   Like tile source types 1 and 4, but with all components being directories.

   URL format::

    <sourceBaseUrl><zoomLevel>/<pixelPosition.z>/<row>/<col>.<fileExtension>

6. DVID ``imageblk`` voxels
***************************

   This type supports loading tiles from voxel data instances in
   `DVID <https://github.com/janelia-flyem/dvid>`_ using
   ``imageblk`` (``uint8blk``, ``rgba8blk``) datatypes.

   For DVID ``imageblk`` tile sources, ``sourceBaseURL`` should reference the
   data instance REST resource with orientation information directly, that is::

       <api URL>/node/<UUID>/<data name>/raw/<dims>/

   ``fileExtension`` may also specify a quality parameter, e.g., ``jpg:80``.

   Because orientations are just permutations of coordinates in the
   voxel volume, each orientation has a slightly different URL format.

   XY format::

    <sourceBaseUrl><tileWidth>_<tileHeight>/<col * tileWidth>_<row * tileHeight>_<pixelPosition.z>/<fileExtension>

   XZ format::

    <sourceBaseUrl><tileWidth>_<tileHeight>/<col * tileWidth>_<pixelPosition.z>_<row * tileHeight>/<fileExtension>

   ZY format (actually YZ, see note)::

    <sourceBaseUrl><tileWidth>_<tileHeight>/<pixelPosition.z>_<row * tileHeight>_<col * tileWidth>/<fileExtension>

   .. note::

       Because DVID prefers YZ axis ordering over ZY, note that tiles for that
       orientation must be transposed to be consistent with other tile source
       types.

7. Render service
*****************

   This tile source type retrieves image tiles from the dynamic
   `render service <https://github.com/saalfeldlab/render/tree/ws_phase_1>`_
   used by the FlyTEM project at Janelia Research Campus.

   URL format::

    <sourceBaseURL>z/<pixelPosition.z>/box/<col * tileWidth>,<row * tileHeight>,<tileWidth>,<tileHeight>,<2^-zoomLevel>/<fileExtension>-image

8. DVID ``imagetile`` tiles
***************************

   This type supports loading tiles from tile data instances in
   `DVID <https://github.com/janelia-flyem/dvid>`_ using
   ``imagetile`` datatypes.

   For DVID ``imagetile`` tile sources, ``sourceBaseURL`` should reference the
   data instance REST resource directly, that is::

       <api URL>/node/<UUID>/<data name>/tile/

   Because orientations are just permutations of coordinates in the
   voxel volume, each orientation has a slightly different URL format.

   XY format::

    <sourceBaseUrl>xy/<zoomLevel>/<col>_<row>_<pixelPosition.z>

   XZ format::

    <sourceBaseUrl>xz/<zoomLevel>/<col>_<pixelPosition.z>_<row>

   ZY format (actually YZ, see note)::

    <sourceBaseUrl>yz/<zoomLevel>/<pixelPosition.z>_<row>_col

   .. note::

       Because DVID prefers YZ axis ordering over ZY, note that tiles for that
       orientation must be transposed to be consistent with other tile source
       types.

Backend Representation
----------------------

Tile source parameters are stored in the ``Stack`` Django model. To create a
new tile source type, one needs only to establish a convention for the integer
that enumerates that type (after communication with the developers) and begin
using it in stacks.

To support cropping, the backend also implements tile sources. To support
cropping for a new tile source type, implement a method
in ``catmaid.control.cropping.CropJob`` like
other ``get_tile_path_<tileSourceType>`` methods that returns the correct URL,
then make sure it is called from the ``CropJob.initialize`` method.

Frontend Retrieval
------------------

The front end implements tile source URL generation in
``django/applications/catmaid/static/js/tilesource.js``. To define a new tile
source type, follow the convention of the existing tiles sources by creating
a function that returns an object with the appropriate ``getTileURL``,
``getOverviewURL``, and ``getOverviewLayer`` methods. The overview URL should
locate a thumbnail of the current stack z-section. Then map the
``tileSourceType`` enumeration of your tile source type to your implementation
in ``CATMAID.getTileSource``.
