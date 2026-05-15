### Camera sensors

Camera sensors capture images of the simulated environment. aiSim can simulate several camera models. Camera models describe and simulate important effects that lenses have on light passing through them that occur with real cameras. Camera models differ mainly in their distortion paramete rs.



### $$\text{Table of Contents}$$

$$\bullet\text{ Common input parameters for}$$all camera models

● Camera models

 o OpenCV pinhole model

 $\bigcirc$ OCam fisheye model

 $\bigcirc$ OpenCV fisheye model

\(\begin{align*}&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{o}\\&\text{\text{o}}\\&\text{\text{o}}\\&\text{o}\\&\text{Mei model

 $\bigcirc$ Othographic model

 $\begin{array}{c}\\\\\\\end{array}$ Perspective model

 $\bigcirc$ AimDistortionModel

 ${}^{\circ}$ Equirectangular

 o F-Theta model

 o EUCM model

● Camera output description● Bounding boxes

 Bounding boxes

 o Bounding box output description

● Sensor output coordinate system

### Common input parameters for all camera models



 How to use the sensor parameters below? See the related aiSim Academy page: Adding sensors to the Ego-vehicle



 www.aimotive.com



|  |  | pre_pwl _pedest al |  |  | int |  |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | pwl_con trol_po ints |  |  | int[2] |  |
|  |  | post_pw l_pedes tal |  |  | int |  |
|  |  | digital _gain |  |  | float |  |
|  |  | cfa_gain |  |  | float[4] | This is a simple, color-filter-specific multiplier that is applied to the final camera output before quantization.The multiplier affects only the following image types: 。 ColorHDRF32CFA 。 ColorCFA 。 ColorBayer 。 ColorBayerRAW12 ColorBayerHIL Considering a 2-by-2 block, the four floats denote the following pixels:[upper-left, upper-right, lower- left, lower-right], in this order. Value range: 0.0-inf.The typical range of value is 0.5-2.0. |
|  |  | output_pixel_v alue_ra nge |  |  | int[2] | Adds a configurable integer-based min-max clamp value that clamps the final LDR camera output to the specified range. Must be exact integers(not percentages), for example,  $[0,255]$  . ● This clamping applies to all non-YUV and non-HDR image types Value range: 0.0-255 or 0.0-4095 where the upper limit comes from the used image type. |



|  | $$\begin{array}{l}\text{ image}_{-}t\\ \text{ type}\end{array}$$ ype |  |  |  | an array of strings ● None ColorCFA ColorHDRF32 RGBA • ColorHDRF32 CFA • IrradianceR GBA • ColorRGBA ColorRGBPla nar ColorBayer ColorBayerR AW12 ColorBayerH IL ColorYUVI420 ColorYUVNV12 ColorYUVYV12 ColorYUVXav ier ● ColorYUVP010 ● AimRawCFA16 $$\begin{array}{l}\\ S\\ e\\ e\\ R\\ a\\ w\\ c\\ a\\ m\end{array}$$ e a $$\begin{array}{l}\\ \\ \\ \\ \\ \\ \\ \\ \end{array}$$ | Specifies the color format from the sensor. Limitations apply: cannot be exported to PNG format. IrradianceRGBA outputs RGB Irradiance(watt per square meter-W/m2) in Float32 RGBA format. Color filtering options You can add color filtering(see color_filter below) for the following image types: • ColorCFA The size(bit per pixel) of the exported image does not change if ColorCFA is enabled. ColorHDRF32CFA ColorBayer ColorBayerHIL ColorBayerRAW12 ColorBayerHIL stores color information in 12 bits, but aiSim sends data in 16 bits, meaning that 12 bits contain values with 4 bits of padding per pixel. ColorBayerRAW12 sends data in 12 bits per pixel. ColorHDRF32CFA sends data as a single-channel 32-bit float. You can debayer images with ImageMagick(with releases newer than July 2022). Example command: magick-verbose-size 2880x1860-depth 8 bayer:filename.tga out. png |
| --- | --- | --- | --- | --- | --- | --- |
|  | color_s pace |  |  |  | an array of strings ● sRGB ● Rec601sRGB ● Rec601Line6 25 ● Rec601Line5 25 * Rec709 | (Optional) We determine a color space via the following properties as of now: ● Color primaries, indicating the gamut of the color space ● White point ● Transfer function/ Gamma-curve(sRGB~2.2 gamma vs Bt1886 OETF~2.4 gamma) Parameter description: sRGB: standard color space for digital content, pipelines, and media, designed for flat monitors (non-CRT) • Rec601sRGB: non standard version of Bt601 with sRGB color space and sRGB gamma curve, but with Bt601 Y'CbCr conversion matrix • Rec601Line625:digital fitted version of(EU) 625-line SDTV's color space found in the Bt601 standard ● Rec601Line525:digital fitted version of(USA) 525-line SDTV's color space found in the Bt601 standard ● Rec709:Bt709 standard's color space for HDTVs with Bt1886-specified gamma-curve(exp. ~2.4 vs sRGB's~2.2) Each Rec* color space also defines the RGBYUV transformation according to their corresponding Bt* standard.The sRGB with ColorYUV* image_type is be treated as Rec709 regarding the YUV transformation. The sRGB(default) color space is supported with all image_type variants. However, R ec601* and Rec709 variants are compatible only with ColorYUV* image_type variants. |



|  | $$\operatorname{col}_{\text{or}}_{=} f$$ $$i 1\text{ ter}$$ |  |  |  |  | Expects a JSON array composed of 12 floats between the range[0.0-1.0]. These floats specify what color a sensor sees by describing 2-by-2 image blocks. For example, the first three numbers of the array describe the color sensitivity of the upper-left pixel of a 2-by-2 block. The second set of three numbers describes the upper-right pixel. The third set is for the lower-left, and the fourth set is for the lower-right. The default value describes an RGGB pattern. You can also describe, for example, patterns as follows: For information, see the Wikipedia article. |
| --- | --- | --- | --- | --- | --- | --- |
|  | depth_type |  |  |  | an array of strings ● None ● Depth16 ● Depth32 | Specifies the image depth type from the sensor. |
|  | segmentation_e nabled |  |  |  | bool | Enables segmentation images. For more information on segmentation, see Segmentation images, IDs, semantic labels, custom attributes, custom tags. |
|  | use_leg acy_segmentati on |  |  |  | bool | If set to true, aiSim exports segmentation images in 8-bit. If set to false, aiSim exports segmentation images in 16-bit. The segmentation image's m_data field is a DoubleEndBuffer type. Internally, DoubleEndBuffer represents its data as bytes, but you can use std::memcpy to copy the data to your uint16_t container(assuming its an std::array): |
|  | use_leg acy_segmentati on |  |  |  | bool | std::memcpy(segmentation_image_msg.segmentation_ids. data(), input_image.m_data.data(), pixel_count* sizeof (uint16_t)); |
|  | use_leg acy_segmentati on |  |  |  | bool | Or to get the value of the i-th element: |
|  | use_leg acy_segmentati on |  |  |  | bool | uint8_t* data= input_image.m_data.data(); uint16_t value=*(data+(i* 2))\|(*(data+(i* 2)+ 1)<< 8) |
|  | use_leg acy_segmentati on |  |  |  | bool |  |
|  | velocit y_type |  |  |  | string | Velocity images are not supported for ray-tracing camera sensors. |
|  | velocit y_type |  |  |  | string | The camera sensor can generate Optical Flow velocity images or Sensor Space velocity images. As these images are derived from the exact movement of points frame-by-frame, none of the computed or externally set(physical) velocity and acceleration values make any difference in the output. Velocity images deal with points, not with objects. For example, a spinning object will have different velocities for most of its points. Possible values: ● None: Velocity image export is disabled. |





|  |  |  |  |  |  | ● The sensor space velocity image represents a 3-dimensional vector for each of its pixels.The three values contain how much the physical point represented by the pixel has moved since the previous frame.The x,y,z axes are defined relative to the camera sensor mounting location and orientation, in the so-called sensor coordinate system. Color image and sensor space velocity image export  Motion blur(motion_blur_enabled) is enabled only if velocity_type is set to OpticalFlow. You can enable only one velocity image type at a time |
| --- | --- | --- | --- | --- | --- | --- |
|  | $$\begin{array}{l}\text{motion}\\ \text{ blur}=\text{ en}\end{array}$$ $$\begin{array}{cc}\text{ blur}&\text{ en}\end{array}$$ abled |  |  |  | bool | Enables the motion blur post-process effect. When using the camera sensor images, motion blur will only be visible for the following image type: ColorCFA ColorHDRF32RGBA ColorHDRF32CFA ColorRGBA ColorBayer ColorBayerRAW12 ColorBayerHIL ColorYUVI420 ColorYUVNV12 ColorYUVYV12 ColorYUVP010 ColorYUVXavier Limitation • Motion blur is not visible on segmentation(seg) or depth type exported images ● Motion blur is only enabled if velocity_type is set to OpticalFlow. ● Motion blur is not supported if ray tracing is enabled for the camera sensor. See more: Camera graphics and realism parameters |
|  | max_mot ion_blu r_sampl es |  |  |  | int | (optional) Sets the maximum sampling for calculating motion blur. Value range: 1-inf.The typical range of value is 16-64 See more: Camera graphics and realism parameters |
|  | object id_enab |  |  |  | bool | When enabled, the application exports camera images The images contain unique IDs for objects in the picture. See also the related parameter render_detailed_object_ids. See also object_ic here for defining export output format. |



|  | $$\underset{=}{\text{ instanc}}$$ $$e_{=}\text{ id}_{=}\text{ en}$$ ab1ed |  |  |  | bool | Gives the pixels' instance ID for instanced objects for cameras with ray-tracing functionality. This is solved by extending the object ID image to contain 64 bits per pixel instead of 32 bits per pixel. ● When this parameter is set to false, the object_id image is not extended with instance ID information. ● When this parameter is set to true, the object ID image will be extended to contain the unique instance IDs as well. This applies to each object in sight that is part of an instanced mesh otherwise, the bits are filled with constant 1 values. See also the related sensor export configuration parameter subtype: instance_id |
| --- | --- | --- | --- | --- | --- | --- |
|  | road_ma rking_g t_rende r_mode |  |  |  | string | Sets how the road marking deterioration is rendered in the Segmentation image output. ● RenderWithDeterioration: Road markings deteriorate in the segmentation image ● RenderWithoutDeterioration: Road markings appear without deterioration in the segmentation image. ● DontRender: The road markings are not rendered in the segmentation image output. |
|  | position |  |  |  | float[3] | Sets the sensor position relative to the ego-vehicle's origin. In meters Value range is the real numbers set. |
|  | rotation |  |  |  | JSON sub-group | Sets the sensor orientation in Euler angles- the yaw, pitch, and roll- that are relative to the ego car s orientation. Interpreted in the Body and Sensor space coordinate system. In degrees. |
|  |  | yaw |  |  | float | Sets the yaw component of the sensor's rotation. Value range:-180-180. |
|  |  | pitch |  |  | float | Sets the pitch component of the sensor's rotation. Value range:-180-180. |
|  |  | roll |  |  | float | Sets the roll component of the sensor's rotation. Value range:-180-180. |
|  | chromat ic_aber ration_ type |  |  |  | string | Sets the model that is used to simulate chromatic aberration. Possible value:STN; none STN model uses the translation to each color channel of an image in 2D pixel space and the scaling of the green color channel relative to the red and blue channels. Example: Download the paper on the STN model: Sensor Transfer Learning Optimal Sensor Effect Image Augmentation_1809.06256.pdf |
|  | chromat ic_aber ration paramet ers |  |  |  | JSON sub-group | Defines the translation of each color channel and scaling of the green channel. |
|  |  | red_ cha nnel tr anslati on |  |  | float[2] | Defines the translation of the red channel. |
|  |  | green_c hannel transla tion |  |  | float[2] | Defines the translation of the green channel. |
|  |  | blue ch annel ranslat ion |  |  | float[2] | Defines the translation of the blue channel. |
|  |  | green c hannel_ scale |  |  | float | Defines the scaling of the green channel. |
|  | visibil k_gt_fl ags |  |  |  | JSON sub-group | See Sensor blockage and contamination. |
|  | blockag e_param eters |  |  |  | JSON sub-group | See Sensor blockage and contamination. |
|  | dof_par ameters |  |  |  | JSON sub-group | See Depth of Field simulation. |



|  | $$i 11\text{ umin}$$ $$\text{ ance}\text{ vi}$$ sualiza tion en abled |  |  |  | bool | Enables illuminance visualization with lsolux lines and heatmap. If this is set to true, the camera generates an illuminance visualization image. The illuminance visualization image shows the illuminance values as isolines and/or heatmap rendered on top of the color image. Isolines show the distribution of the illuminance on a visible surface. See also: \bullet illuminance_visualization_parameters on this page. ● illuminance_visualization subtype on page Exporting sensor data. |
| --- | --- | --- | --- | --- | --- | --- |
|  | $$i 11\text{ umin}$$ $$\text{ ance}\text{ vi}$$ sualiza tion en abled |  |  |  | bool |  |
|  | illumin ance_vi sualiza tion_pa rameters |  |  |  | JSON sub-group |  |
|  |  | illumin ance_ty pe |  |  | string | Sets the illuminance type. Possible values: ● Planar: Uses Planar illuminance values ● Radial: Uses Radial illuminance values |
|  |  | visuali zation_ type |  |  | array of strings | Sets the type of the illuminance visualization. Possible values: ● Isoline: Visualizes the illuminance values as isolines ● Heatmap: Visualizes the illuminance values as a heatmap |
|  |  | visuali zation_ type |  |  | array of strings | e You can combine the illuminance visualization effects by setting the following: ["Isolines","Heatmap"] An empty array is not allowed. |
|  |  | isoline _values |  |  | array of floats | Sets the values assigned to the isoline curves. Defines which iso curves aiSim visualizes.The maximum number of floats in the array is 128. Floats above the limit of 128 are discarded. |
|  |  | isoline _values |  |  | array of floats | See also Contour line. |
|  |  | isoline _thickn ess |  |  | float | Sets the thickness of the isolines in pixels. Valid only if the Isolines value is used for visualizat ion_type. Must be 0.0 or greater. |
|  |  | heatmap _opacity |  |  | float | Sets the opacity of the heatmap visualization. Valid only if the Heatmap value is used for visualiza tion_type.The valid value range is between 0.0 and 1.0(inclusive). |
|  | camera exposur e_contr oI |  |  |  | JSON sub-group | Describes the parameters for physically-based camera exposure calculation. |
|  |  | type |  |  | string | ● ManualFromSensorConfiguration: The camera exposure control is manual; the camera exposure parameters come from the camera sensor configuration(see camera_exposure_p arameters below). In this case, each camera in the sensor configuration can have different manual exposure settings. ● ManualFromEnvironmentConfiguration: The camera exposure control is manual; camera exposure parameters come from the Environmental configuration file. Affects all camera sensors in a sensor configuration file. ● AutoFromExposure LUT: The camera exposure control is automatic; the exposure value is determined by a lux-exposure look-up table. ● AutoFromAverageLuminance: The camera exposure control is automatic; the autoexposure calculation is based on the average luminance of the light captured by the camera. o See also related parameters: auto_exposure_luminance_key_value;auto_expos ure_luminance_min;auto_exposure_luminance_max See page Camera exposure control. |
|  |  | auto_ex posure_ luminan ce_key_ value |  |  | float | Used only if AutoFromAverageLuminance is set under type. ● auto_exposure_luminance_key_value: The average luminance is mapped to this exposure value for automatic exposure calculation. ● auto_exposure_luminance_min: Sets the lowest accepted average luminance for automatic exposure calculation. |



|  |  | auto_ex posure luminan ce min |  |  | float | • auto_exposure_luminance_max: Sets the highest accepted average luminance for automatic exposure calculation automatic exposure calculation. For more information on the parameters and the implementation, see the following article:https://knarkowicz.wordpress.com/2016/01/09/automatic-exposure/  See page Camera exposure control |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | auto_ex posure luminan ce_max |  |  | float | • auto_exposure_luminance_max: Sets the highest accepted average luminance for automatic exposure calculation automatic exposure calculation. For more information on the parameters and the implementation, see the following article:https://knarkowicz.wordpress.com/2016/01/09/automatic-exposure/  See page Camera exposure control |
|  |  | lux_inc rement for_lut _keys |  |  | float | $$\text{ Sets the increment of lux key values assigned to each exposure value in the auto exposure lut,}$$ starting from 0.0.  $\sim$  See page Camera exposure control. |
|  |  | auto_ex posure_ lut |  |  | array of floats | Used if AutoFromExposureLUT is selected as a camera_exposure_control type. Lists lux- exposure value pairs.  $\mathcal{V}$  For an example auto_exposure_lut code snippet, see the example on page Camer a exposure control. |
|  |  | camera exposur e_param eters |  |  | JSON sub-group | The three parameters in this group are used to control manual camera exposure if the ManualFromS ensorConfiguration parameter is set as a type of camera_exposure_parameters. If you want to set the same manual camera exposure control parameters for all cameras in a sensor configuration, then set global camera_exposure_parameters in the Environmental configuration, then set ManualFromEnvironmentConfigurati on parameter as a type of camera_exposure_parameters. |
|  |  |  | f_stop |  | float | Sets the ratio of the focal length to the diameter of the aperture. The value is dimensionless. The value must be a positive number greater than 1. A typical range is 1.4-45.0. |
|  |  |  | sensiti vity |  | float | Controls how the light reaching the sensor is quantized. Often referred to as the ISO. A higher sensitivity value results in a lighter image and vice versa. The value must be a positive number greater than 0. A typical range is 0.001-10000.0. A high ISO value does not cause digital noise. |
|  |  |  | shutter _speed |  | float | Controls how long the aperture remains open. Expressed in seconds. Higher shutter speed results in a lighter image and vice versa. The value must be a positive number greater than 0. A typical range is 0.001-0.02. |
|  | propert ies |  |  |  | JSON sub-group | Based on the calculated location of the sensor, images must be generated that cover the area of space from which light can enter the lens(in other words, these are the"pre-distortion rendering images"). This can be, for instance, a single image("environment_mapping_type":"None") or a total of six images("environment_mapping_type":"Cube_6_Face"), depending on the characteristics of the simulated camera. |
|  |  | environ ment_ma pping_t ype |  |  | None; Tetrahedron 4_Face;Cube_6_F ace; Auto_100; Auto_99_7; Auto_95; Auto_68 | Defines the number of images the camera uses from which light can enter the camera lens. The auto values for environment mapping selection are the following four numbers specifically due to the 68-95-99.7 rule. We suppose that the sensor distortion follows a normal distribution. Then we calculate the standard deviation(), and following the 68-95-99.7 rule, the four instances can be deduced. Auto_* values can be used to allow the program to find the optimal environment mapping type(None \| Cube_6_Face) and corresponding render_y_fov and render_resolution_per_face. You can read more on the Auto* values under the Camera distortion models section on the Camer a graphics and realism parameters page. |
|  |  | near_pl ane; far_pla ne |  |  | float | The camera renders the area between the near plane and the far plane; in meters. The value for near_plane must be less than the far_plane value and vice versa. The typical value range for near_plane is 0.001-0.1.The typical value range for far_plane is 500.0- 5000.0. |



|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | If you want to set your perspective camera model's horizontal FoV, jump to the  $f\circ v x_{-} d$  eg parameter in the Perspective model on this page. |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | Controls the field of view of the pre-distortion image that the camera sensor uses to collect light. The values represent degrees. Value range: 1.0-180.0. |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | There is no need to set the render horizontal(x) FoV separately since it is derived from render_y_fov. |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | If you experience an image artifact in the output of your camera sensor(e.g. grey frame and thus truncated image), try increasing render_y_fov up to 120 degrees. For wide FoV cameras above 120 degrees(e.g. fisheye), use"environment_mapping_type":"Cube_6_Face". Note that Cu be_6_Face might have an impact on performance. |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | render_y_fov parameter is disregarded if"environment_mapping_type": "Cube_6_Face". |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | Example of an image artifact when render_y_ fov is too low(notice the grey frame around the image): [CAMERA] MEI(IMAGE)  |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float |  |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float |  |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | Note for OpenCV models If you want to change the field of view of your OpenCV camera, you will also need to update the focal length accordingly. The focal length and FoV are used together to calculate the width and height of the captured image in pixels. You can use the following formula to get the focal length for the intended width and FoV for both x and y: |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float | focal_length=(width/ 2)* tan(render_y_fov/ 2) |
|  |  | $$\text{ render}_{=}$$ $$y_{\text{fov}}$$ |  |  | float |  |
|  |  | auto_en vironme nt_mapp ing_typ e_rende r_resol ution_s cale |  |  | float | This parameter refers to the number by which the pre-distortion image resolution is multiplied. It is effective only when the environment_mapping_type is set to Auto_*. |
|  |  | auto_en vironme nt_mapp ing_typ e_rende r_resol ution_s cale |  |  | float | The value must be a positive number greater than 0. A typical range is 0.25-4.0. |
|  |  | auto_environme nt_mapp ing_typ e_rende r_y_fov _bias |  |  | float | This is the number that is added to the auto-calculated pre-distortion image vertical field of view. It is effective only when the environment_mapping_type is set to Auto_*. The value must be a positive number greater than 0. A typical range is 0.0-10.0. |
|  |  | max_ren dering_angle_b ias_deg |  |  | float | If a full 360-degree environment_mapping_type is used(i.e.,Cube_6_Face,Tetrahedron_4 Face or Auto_* with a large FoV camera), the image is culled using the sensor's effective viewing angle.This bias applies to that viewing angle(in degrees). A smaller value increases performance as more regions of the 360-degree rendering can be culled. A larger value renders more areas outside of the sensor's visible area, but it also allows screen space effects(ambient occlusion and water reflections) to sample data from the outer regions. The value must be a positive number greater than 0. A typical range is 0.0-10.0. |
|  |  | max_blo om_depth |  |  | int | See Camera graphics and realism parameters. The value must be a positive number greater than 0. A typical range is 4-6. |



|  |  | is_ray_ tracer |  |  | bool | Enables ray-tracing-based camera sensors. |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | is_ray_ tracer |  |  | bool |  If you enable ray-tracing for a camera sensor, please also add raytrace_properties (see one row below) to your sensor configuration. You may especially want to add a de noiser_type to your ray-tracing camera sensor if you experience noisy images(such as black or white dots or artifacts). |
|  |  | is_ray_ tracer |  |  | bool |  |
|  |  | is_ray_ tracer |  |  | bool |  Limitations with ray-tracing cameras Ray-tracing cameras have a limited feature set compared to non-ray-tracing cameras. The following limitations are in effect if ray tracing is enabled: ● Motion blur is not supported ● Velocity output: parameter velocity_type must be set to None ● supersampling_enabled must be set to false. You may increase the samples_per_pixel parameter instead of using Supersampling for ray-tracing cameras for a similar result. |
|  |  | raytrac e_prope rties |  |  | JSON sub-group | Contains ray-tracing properties |
|  |  | raytrac e_prope rties |  |  | JSON sub-group |  is_ray_tracer must be set to true to enable ray-tracing properties. See page Prerequisites and installation for hardware specifications and limitations on ray-tracing capabilities. You may want to refer to an example ray-tracing camera sensor implementation, for example:aiMotive\aisim_gui- \data\calibrations\raytrace_camera.json |
|  |  |  | enable accumul ation |  | bool | Enables sampling of previous camera frames as long as the camera state remains unchanged. The camera state usually changes when something moves in the camera's view. |
|  |  |  | enable accumul ation |  | bool | A This setting can improve image quality in very limited use cases where there are no dynamic vehicles, and the ego-vehicle stays still for a longer period of time. Avoid enabling it on scenes with moving actors, as their movement might be incorrectly accumulated, resulting in ghosted images. |
|  |  |  | enable accumul ation |  | bool |  |
|  |  |  | sky_and sun_li ghting_ samples |  | int | Sets the number of samples determining the sky visibility lighting factor. More samples provide higher quality sky lighting and soft sun shadows. The value must be a positive number greater than 1. A typical range is 4-16. |
|  |  |  | light_s amples |  | int | (optional) Sets the number of samples determining the lighting coming from artificial light sources. If not set, the number of light sources in the scene is used. You can speed up rendering if you reduce the light samples compared to the number of lights present in the scene. The sun is always sampled. making this more relevant for scenes using artificial lights. The value must be a positive number greater than 1. |
|  |  |  | samples _per_pi xel |  | int | Sets the number of samples to be calculated and averaged per-pixel. Multiple samples provide a smoother image. Value range:1-inf.The typical range of value is 1-32 but 1 is recommended. |
|  |  |  | batch_c ount |  | int | With this parameter, you can split samples_per_pixel workloads into a number of batches. If rendering took so long that the GPU would timeout, you can avoid timeouting by splitting the workload into batches. Value range:0-inf.but1is recommended. |
|  |  |  | maximum distan ce |  | float | Sets the maximum rendering distance from the camera, in meters. The value must be a positive number greater than 1. A typical range is 5.0-5.000. |
|  |  |  | use_fir efly_fi lter |  | bool | Enables a logic to reduce the occurrence of“firefly” artifacts by calculating the variance across neighboring pixels and rejecting outliers. For an example usage, see also: Camera graphics and realism parameters |



|  |  |  | denoise r_type |  | string | Enables the render engine's runtime GPU-based image denoiser logic. The implementation uses the ntel Open Image Denoiser 2.0 library. For an example usage, see also: Camera graphics and realism parameters Values: ● None • LowQuality • BalancedQuality ● HighQuality  Supported GPUs ●NVIDIA GPUs with Volta,Turing,Ampere,Ada Lovelace,and Hopper architectures● AMD GPUs with RDNA2(Navi 21 only) and RDNA3(Navi 3x) architectures architectures If you set denoiser_type but you do not have a supported GPU, aiSim falls back to Intel's CPU-based denoising technology. CPU-based denoising has a negative impact on rendering speed. |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  | max_den oiser_m emory_mb |  | int | Limits the VRAM usage of the denoiser, expressed in megabytes. By limiting memory usage, you can avoid running out of memory. By default, the VRAM usage is not limited(-1). The value must be greater than-1. But the default(not limited) is recommended. |
|  |  |  | prefer_ cpu_den oiser |  | bool | By default, aiSim uses the GPU to denoise ray-tracing camera images. If this fails for any reason(e. g.,unsupported GPU),aiSim returns to CPU-based denoising, which is usually slower than GPU- denoising. However, there are cases when CPU-denoising is a better choice, for example, if the computer runs out of VRAM(denoising is a VRAM-heavy task). If you set the parameter to true, aiSim is forced to use CPU-denoising. |
|  |  |  | seconda ry_boun ces_type |  | string | Sets the type of a ray's secondary bounce type. Values: ● Specular:After the first camera ray hit, the system generates specular rays. ● SpecularAndDiffuse: After the first camera ray hit, the system generates diffuse and specular rays. |
|  |  |  | gaussia n_splat ting_hi t_buffe r_size |  | int | Sets the size of the hit buffer for the Gaussian splatting's ray-tracing renderer.The size must be higher than 1. The hit buffer size determines how many of the nearest splats are considered during raytracing. If a ray that is cast from the camera's pixel intersects,e.g.,16 splats, and the buffer size is 6, it means that aiSim processes that pixel split in three steps: the first six splats at once in the first step, the second six in the second step, and the remaining four in the third step. You may want to set this parameter if the computer running aiSim works optimally with different splitting. |
|  |  |  | gaussia n_splat ting_so rting_m ode |  | string | Sets the sorting mode for the Gaussian splatting's ray-tracing renderer. Possible values: ● SortByMRP: Sorts points by the maximum response from the point along the ray. ● SortByDistanceToPointCenter: Sorts points by distance to the splat's center. i MRP:Maximum Response Point.Splats have a 3D extent.When a ray (mathematically, it is a half-line) intersects a splat, it passes through some volume of space described by the splat. The strength of the splat weakens according to a Gaussian distribution.The MRP is the point along the half-line where the splat takes on its strongest value. Sorting mode: The splats are sorted during tracking from a distance from the camera. aiSim passes through splats in a sorted order, which affects the visual effect.The two available sorting modes refer to the distance measurement used to sort the splats.You may want to set this parameter if the Gaussian splat is trained differently and the camera image appears unappealing. |
|  |  |  | max_dep th |  | int | Sets the raytrace's maximum depth. During ray-tracing, the ray is traced from the camera to the light source in a reversed manner. If max_depth is set to 1, aiSim displays only the result of rays shot from the camera, which will result in an image of a directly illuminated scene(like in rasterization). If you increase this parameter, you add more reflection rays, which will result in more accurate indirect illumination. Greater depth has an impact on the performance. |
|  |  |  | minimum distan |  | float | Defines the minimum rendering distance from the camera. Used for image culling |
|  |  | gpu_id |  |  | int | (optional) Specifies the GPU's identification index to be used for camera simulation. If not set, the GPU scheduler assigns a GPU to a camera sensor. Indexing starts from zero. |



|  |  | hil _off set |  |  | int | Defines which HIL hardware port is to be used to output the image. |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | post_pr ocess_r ender_p aramete rs |  |  | JSON sub-group | A sub-block for camera image post-processing techniques. |
|  |  |  | saturat ion |  | float | Saturation defines a range from pure color(100%) to gray(0%) Value range:1.0-0.0. |
|  |  |  | bloom i ntensity |  | float | See Camera graphics and realism parameters. Value range:0.0-1.0.The typical range of value is 0.0-0.1. |
|  |  |  | use_blo om_fire fly_fil ter |  | bool | See Camera graphics and realism parameters. |
|  |  |  | sharpen streng th |  | float | $$\text{ Image sharpening refers to any enhancement technique that highlights edges and fine details in an}$$ image.This parameter controls the sensitivity of sharpening. Value range:0.0-1.0.Default is recommended. |
|  |  |  | sharpen _limit |  | float | Sets the amount of sharpening influence on the image. Value range:0.0-1.0.Default is recommended. |
|  |  |  | contras t_center |  | float | Sets the amount of contrast influencing the image. Value range:0.0-1.0.Default is recommended. |
|  |  |  | contrast |  | float | This parameter controls the sensitivity of contrast. Value range:0.0-2.0.Default is recommended. |
|  |  |  | white_m ultipli er |  | float | After tone mapping, you can set the brightness using this parameter Value range:0.0-16.0.Default is recommended. |
|  |  |  | color_t emperat ure |  | float | Sets the color temperature in Kelvin. Value range:1000.0-27000.0. |
|  |  |  | color_t emperat ure_wei ght |  | float | Sets the weight of the color temperature. Value range:0.0-1.0. |
|  |  |  | color_g rading_lut_uri |  | string | (optional) Sets a URI pointing to a 3D DDS, a texture file, or a CUBE file containing a color mapping LUT. |
|  |  |  | tonemap per |  | string | Possible values: Filmic; FilmicACES; Reinhard; AMDFidelityFXLPM; Linear.Tone mapping is a technique used to map one set of colors to another to approximate the appearance of high-dynamic-range images in a medium that has a more limited dynamic range. |
|  |  |  | 1pm_par ameters |  | JSON sub-group | A sub-block for LPM parameters. Applies only if AMDFidelityFXLPM is selected as a tonemapper. For detailed background and a complete list of LPM parameters, see here. From the complete list, only those parameters are configurable for aiSim that are listed below. |
|  |  |  |  | sof t_gap | float | Controls the extent of the feather region in out-of-gamut mapping. The range varies from 0 to a little over zero; 0=clip. |
|  |  |  |  | exp osure | float | Sets the number of stops between hdrMax and 18% mid-level on input. |
|  |  |  |  | con trast | float | Sets the contrast input range between 0.0 and 1.0. Value 0.0 means no extra contrast, while value 1.0 means maximum contrast. |
|  |  |  |  | sho ulder_c ontrast | float | Defines shoulder shaping. Value 1.0 means no change(fast path). |
|  |  |  |  | sat uration | float[3] | Sets the per-channel saturation adjustment. Use a value<0 to decrease,0 to apply no change, while>0 to increase saturation. |
|  |  |  |  | out _gamut_r | float[2] | Sets the chroma coordinates for the output color space(Red) |
|  |  |  |  | out _gamut_g | float[2] | Sets the chroma coordinates for the output color space(Green). |



|  |  |  |  | out _gamut_b | float[2] | Sets the chroma coordinates for the output color space(Blue) |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  | out _gamut_w | float[2] | Sets the chroma coordinates for the output color space(White). |
|  |  |  |  | cro sstalk | float[3] | Decides how the input colors, when overexposed or going beyond the SDR range, should shape into the color gamut. One channel must be 1.0, the rest can be<= 1.0 but not 0.0. |
|  |  | render resolut ion_per _face |  |  | unsigned int | Defines both the width and height of pre-distortion images. In the case of Tetrahedron 4 Face or Cube_6_Face, it defines the width and height of a single image Value range:1-32768. |
|  |  | supersa mpling enabled |  |  | bool | Enables the supersampling feature. |
|  |  | $$\text{ interna}$$ l_resol ution_s cale |  |  | string | This parameter controls the camera sensor's rendering performance by upscaling or downscaling the resolution of aiSim's internal camera resources. Camera resources are those fundamental textures that build up the camera sensor's image. You can achieve either a considerable performance improvement or an improvement on the image quality by using this parameter. Possible values are the following: ● Double: Improves the image quality in the same way as Supersampling(i.e., by rendering the camera resources at double the resolution). o If supersampling_ enabled is set to true, this internal_resolutio n scale parameter is disabled. o The Double parameter is not supported if raytracing is enabled. ● Half:Improves performance by rendering the camera resources at half the resolution.  $\overrightarrow{\text{i}}$  Uses the AMD FidelityFX Super Resolution feature. ● One: Uses the default camera resource resolution.  $\overrightarrow{\text{l}}$  This parameter does not affect the resolution of the output sensor images. Do not use float values for this parameters. Use only the strings listed as possible A values. AISIM AISIM From left to right: One and Half |
|  |  | ssao_sa mples |  |  | int | Screen Space Ambient Occlusion(SSAO) is a computer graphics technique for efficiently approximating the ambient occlusion effect in real-time. This parameter sets the sampling. Setting 0 disables the feature. Value range: 0-128. Recommended value is 64. |
|  |  | smaa_en abled |  |  | bool | Enables the SMAA filter, which provides additional edge smoothing on the images. |



|  |  | $$\text{ render}.$$ detaile d_ objec t_ids |  |  | bool | object id enabled must also be enabled along with this parameter. The different meshes of objects(e.g., windshield, tire, rims, etc.) receive unique IDs, thus giving a more detailed object ID image. |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | lens_fl are int ensity |  |  | float | (optional) Sets the intensity of the lens flare effect. Value range:[0..1], where 0 means no effect. 1 means that the lens fare intensity equals the sun's full luminous intensity, resulting in blown highlights. The lens flare effect intensity value is expressed as a percentage of the sun's intensity. Therefore, we recommend using~0.0001 as lens_flare_intensity. The lens flare effect considers camera or distortion type, camera position, camera rotation, and object obstruction, and the application renders the effect accordingly. The lens flare is visible only when the sun is directly visible in the camera's field of view. Use the Sunlight Direction panel in the Environment workspace of aiSim GUI to set the incoming sunlight's direction. |
|  |  | disable _pixel_ culling |  |  | bool | aiSim's rendering engine uses culling for objects(meshes) smaller than 1 pixel by default. This is to decrease rasterization overhead when drawing distant objects with a large number of polygons. If an object is so far that its size on the camera image is smaller than one pixel, the render system will not draw it. In some cases, you may want to disable this feature by setting the parameter to true. |
| bounding box_con fig |  |  |  |  | JSON sub-group | (optional) If enabled, the camera sensor provides model space information about the objects within the camera's view. |
|  | visuali ze |  |  |  | bool | Enables bounding box visualization on the camera viewports. Bounding boxes will not be rendered for the exported camera sensor images. A |
|  | semanti c_class es_by_a ctor |  |  |  | array of strings | Lists the bounding box segmentation classes to be detected,e.g.,Car,Truck.See default_segmen tation.json for possible class names. e You can find the default_segmentation.json under the following paths: ●Windows:&LOCALAPPDATA\aiMotive\totoolchains\tc_core- \clients\data\segmentation_settings\default_s egmentation.json ● Ubuntu:/opt/aiMotive/toolchains/tc_core- /clients/data/segmentation_settings/default_segmentation. json When an element is in the semantic_classes_by_actor list, its bounding box will appear based on the actor. |
|  | semanti c_class es_by_m esh |  |  |  | array of strings | Lists the bounding box segmentation classes to be detected,e.g.,Car,Truck.See default_segmen tation.json for possible class names. The following strings cannot be added to the list: "Car","Van","Truck", "Trailer","Bus" When an element is in the semantic_classes_by_mesh list, its bounding box will appear for each mesh. The same element can appear in both the semantic_classes_by_actor and the se mantic_classes_by_mesh lists.In this case, its bounding box will appear both for the actor and the mesh. |
|  | occlusi on_enab |  |  |  | bool | Enables per-pixel occlusion calculation. i The bounding box submodule of the camera sensor uses visually-based occlusion calculation. The bounding box submodule takes an image of the scene with the same camera parameters and determines occlusion based on the image. Please note that the Radar sensor uses a different method for occlusion calculation. |
|  | precise_bbox |  |  |  | bool | Enables pixel-perfect bounding box calculation for objects. Additionally, if an object is occluded, the application can provide partial bounding box information for the part that is exposed to the camera sensor. |



|  | capture instan ces |  |  |  | bool | Captures bounding boxes of individual instances in instanced meshes. The capture_instances and rage_in_meter(see row below) parameters help detect instances via the BoundingBoxCalculator. |
| --- | --- | --- | --- | --- | --- | --- |
|  | $$\text{ range}=\frac{i}{\text{ n}}\text{ meter}$$ $$n_{\text{=}}\text{ meter}$$ |  |  |  | float | Sets the detection radius of bounding boxes in meters. If the range_in_meter parameter is set, bounding boxes will only be detected within the given range. If the range_in_meter parameter is set to 0, no distance will be set for non-instanced objects. However, for instanced objects, there will still be a default detection radius value of a maximum of 500 meters. |
| lane_con fig |  |  |  |  | JSON sub-group | The camera sensor is able to output information(e.g., the polyline coordinates) about the lane separators in each camera image.The output format is JSON(see Exporting sensor data).The content is described by the LaneMessage, which is in the SDK Doxygen documentation. e For visualizing lane separators, use aiSim Server with the aisim_client sample application. |
|  | distanc e_along _lane_i n_meter |  |  |  | float | (optional) Defines the lane detection range along the road in meters. |

### Camera models

### OpenCV pinhole model



"model":"OpenCVPinhole"

This model describes the OpenCV pinhole camera.

### Parameter description



| Parameter | Parameter | Type | Description |
| --- | --- | --- | --- |
| distortion_parame ters |  | JSON sub- group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | principal_point | float[2] | Sets the principal point of the camera(in pixels) |
|  | focal_length | float[2] | Sets horizontal and vertical focal lengths in pixels. An array of two floats. |
|  | distortion_coefficients | float[5] | Sets coefficients for the undistortion 2D-to-3D polynomial for cameras. An array of five floating-point numbers. Expected values:[k1,k2,p1,p2,k3] |
|  | rational_model_coeffici ents | float[3] | (optional) Adds additional[k4,k5,k6] coefficients to the model to realize a rational model. |

### OCam fisheye model



"model":"OcamFisheye"

This model describes the OCam fisheye camera.

### Parameter description



| Parameter | Parameter | Possible values | Explanation |
| --- | --- | --- | --- |
| distortion_parameters |  | JSON sub- group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | principal_point | float[2] | Sets the principal point of the camera(in pixels) |
|  | polynomial_coefficients | float[5] | Sets coefficients for the 2D-to-3D polynomial for a camera |
|  | inv_polynomial_coefficien ts | float[16] | Sets the coefficients for the 3D-to-2D polynomial for a camera An array of 16 floating-point numbers. |

### OpenCV fisheye model



"model":"OpenCVFisheye"

This model describes the OpenCV fisheye camera.

### Parameter description



| Parameter | Parameter | Type | Description |
| --- | --- | --- | --- |
| distortion_p arameters |  | JSON sub- group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | principal_poi nt | float[2] | Sets the principal point of the camera(in pixels) |
|  | focal_length | float[2] | Sets horizontal and vertical focal lengths in pixels. An array of two floats. |
|  | distortion_co efficients | float[4] | Sets coefficients for the undistortion 2D-to-3D polynomial for cameras. An array of four floating-point numbers. Expected values:[k1,k2,k3,k4] |
|  | k0 | float | In the original Fisheye model, there is a constant 1 coefficient. Some use cases require this constant to be changed. By default, the value is 1.0- no change to the original model. |

### Mei model



$$
\text{"model":"Mei"}
$$

The'Mei'(Single View Point Omnidirectional Camera Calibration) camera model can describe both pinhole and fisheye camera models.

### Parameter description



| Parameter | Parameter | Possible values | Explanation |
| --- | --- | --- | --- |
| distortion_para meters |  | JSON sub- group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | principal_point | float[2] | Sets the principal point of the camera(in pixels) |
|  | focal_length | float[2] | Sets horizontal and vertical focal lengths in pixels. An array of two floats. |
|  | distortion_coeff icients | float[5] | Sets coefficients for the undistortion 2D-to-3D polynomial for pinhole cameras. An array of five floating-point numbers. Expected values:[k1,k2,p1,p2,k3] |
|  | Xi | float | The parameter describes the mirror shape. It sets the perpendicular distance between the image plane and the center point of the unit sphere. |

### Orthographic model



"model":"Ortho"

This camera model uses orthographic projection where an object's size in the rendered image stays constant regardless of its distance from the camera.The size of the objects depends on the amount of zoom applied.

### Parameter description



| Parameter |  | Possible values | Explanation |
| --- | --- | --- | --- |
| distortion_parameters |  | JSON sub-group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | zoom | float[2] | Sets how many pixels are equivalent to one meter in the image. Defines the X and Y coordinates. |

### Perspective model



"model":"Perspective"

This camera model represents the"perfect" pinhole camera.



The perspective model is an idealized camera model that is not meant to simulate real-world cameras but to be used as a camera viewport in the aiSim GUI.



The perspective model uses a perspective projection matrix when rendering the simulated world. This model only uses a field-of-view parameter that sets the angle of the viewing frustum.

When using this Perspective model, the field of view can be calculated using the focal length, but the calculation needs other camera parameters as well:

fov= 2*\arctan(x/(2*f))

where:

f is the focal length,

x is the diagonal of the modeled sensor.

E.g.: a 10 mm focal length with a 36 mm sensor diagonal would result in an FoV of 121.9°.

### Parameter description



| Parameter |  | Possible values | Explanation |
| --- | --- | --- | --- |
| distortion_parameters |  | JSON sub-group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | fovx deg | int | Sets the Field of View for the camera model. In degrees. $$\text{ Note: the}\gamma\text{ component of the FOV is calculated by the camera's resolution and the fovx deg.}$$ |

### AimDistortionModel



"model":"AimDistortionModel"

This camera model can read a look-up table(LUT) in DDS format(four components, 32-bit floats). Using this LUT and the AimDistortionModel,you can create and use a custom camera distortion in aiSim.



To use the AimDistortionModel, you must set the environment_mapping_type parameter to Cube_6_Face. See Common input parameters for all camera models at the top of this page.

To create the LUT, use the following algorithm:

for v in sensor.height:for u in sensor.width:ray= ImageToView(u+ 0.5, v+ 0.5)lut[u, v]=(ray.x,-1.0* ray.y, ray.z, 1.0)

Where the ImageToView function implements the image--> view(or the 2D--> 3D) functions of the new camera model. The result should be a LUT in DDS format with the same resolution as your camera.



There is a sample Python script file available in the aiSim package:

aisim_sdk-<ver>Release<OS>/aiSim_sdk-<version>Release<OS>/aisim-<version>/tools/generate_aimdistortion_lut.py

### Parameter description



| Parameter |  | Possible values | Explanation |
| --- | --- | --- | --- |
| distortion_parameters |  | JSON sub-group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | lut_uri | string | Sets the URI to the LUT containing the camera distortion parameters. |

### Equirectangular model

"model":"Equirectangular"

The equirectangular model uses equirectangular projection when rendering the simulated world. It can be used to capture a wide angle of the scene in a single image.

### Parameter description



| Parameter |  | Possible values | Description |
| --- | --- | --- | --- |
| distortion_parame ters |  | JSON sub- group | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | horizontal_fov_limit s_deg | float[2] | Specifies the horizontal FoV limits of the camera in degrees. The expected range is between-180° and+180°. |
|  | vertical_fov_limits_ deg | float[2] | Specifies the vertical FoV limits of the camera in degrees. The expected range is between -90° and+90°. |

### F-Theta model



"model":"FTheta"

The F-Theta camera model is an alternative to the Mei model; it can describe fisheye and pinhole cameras.



For more information, see the following paper: nvidia_ftheta.pdf

### Parameter description

When using the F-Theta camera model, you must add the coefficients of both the forward and backward polynomials in the camera configuration.The ftheta_calculator.py is a Python script that can calculate the coefficients of either polynomial(forward or backward) based on the coefficients of the other one. The script takes the sensor resolution, the principal point(optional), and the coefficients of one of the polynomials(forward or backward) for which we want the inverse model coefficients to be calculated.

The scrip is located under the aiSim-sdk-<ver>/tools/ftheta_calculator.py path.

The script works in either direction(forward-> backward, backward-> forward). It first tries to fit a polynomial to the inverse. If no polynomial satisfies the error criterion(an absolute error less than 0.5 pixels by default, but also see the max_valid_reprojected_ray_pixel_distance parameter), the script continues with an extension  ${}_{e(\theta)}=l_{0}\theta^{\frac{1}{2}}+l_{1}\theta^{\frac{1}{3}}+\cdots+l_{p}\theta^{\frac{1}{p+2}}$  , and tries to find its coefficients for a better fit.

The output is the coefficients of the corresponding inverse polynomial. If no polynomial matching the error criterion is found, then the output is the coefficients of both the polynomial and its extension.

### Example usages:



In both examples, select the model with a flag(--forward or--backward) for which you specify the coefficients at the end of the argument list after double dashes.

1. Calculate the coefficients of the forward polynomial based on the backward polynomial:

ftheta_calculator.py--resolution 1280 720--principal_point 641.12 358.77--backward-- 0.00.002405

2. Calculate the coefficients of the backward polynomial based on the forward polynomial:

ftheta_calculator.py--resolution 1280 720--principal_point 641.12 358.77--forward-- 0.0415.800415



For the complete list of available options, run the script with the--help option.



| Par am eter |  | P $$\begin{array}{l}\\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \end{array}$$ v au es | Description |
| --- | --- | --- | --- |
| di st or ti on _P ar am et ers |  | $$JSOON$$ S u b - $$\begin{array}{l}g\\ r\\ 0\\ up\end{array}$$ | Specifies the lens distortion parameters that are specific to the given camera model. |
|  | princi pal _po int | f  $0$  at  $[2]$  | Sets the principal point  $\left[u_{0},v_{0}\right]$  of the camera(in pixels). |
|  | focal length | f  $0$  at  $[2]$  | (optional) Sets the horizontal and vertical focal lengths(in pixels). If not set, the model assumes focal lengths equal to the coefficient  $k_{-}1$  |



|  | forwar d_coef ficien ts | fl 0 at [n] | Sets the coefficients of the forward polynomial  $f(\theta)=k_{0}+k_{1}\theta+k_{2}\theta^{2}+\cdots+k_{n}\theta^{n}$  that maps the angle to the distance to the principal point in image space r_d, from the lowest to the highest degree. |
| --- | --- | --- | --- |
|  | backwa rd coe fficie nts | fl 0 at m] | Sets the coefficients of the backward polynomial  $b(r)=j_{0}+j_{1} r+j_{2} r^{2}+\cdots+j_{m} r^{m}$  that maps the distance to the principal point in image space  $r_{d}$  to the angle of the ray with the optical axis, from the lowest to the highest degree. |
|  | max_va lid_re projec ted_ra y_pixe l_dist ance | fl  $\underset{0}{o}$  at | Sets the maximum pixel distance that a reprojected ray can differ from the original pixel's location. This parameter relates to the ftheta_calculator.py calculator script(see above) that can calculate the coefficients of either polynomial(forward or backward) based on the coefficients of the other one. Due to the challenges of inverting polynomials, there might be 1-2 pixel inaccuracies in the calculated result. By default, aiSim filters errors larger than 0.5 pixels and changes their coloring to black on the final camera image. This threshold might be too strict for certain use cases, resulting in black artifacts. You can raise the error threshold to improve the image quality. There is a suggested value for this parameter that is calculated by the ft heta_calculator.py script, see the"Max error" line. |
|  | forwar d_exte nsion coeffi cients | fl0at[k] | Sets the coefficients of the forward polynomial's extension  $e(\theta)=l_{0}\theta^{\frac{1}{2}}+l_{1}\theta^{\frac{1}{3}}+\cdots+l_{p}\theta^{\frac{1}{p+2}}$  , from the lowest to the highest degree. It is used in rare cases where the backward polynomial's inverse is difficult to approximate by a polynomial. |
|  | affine trans form_p aramet ers | f1oat[3] | Sets the parameters c,d and e of the affine transformation that is applied to the image space coordinates. The equation of the forward transformation(ray2pixel) in the nvidia_ftheta.pdf is extended with the affine transformation as follows: $$\left[\begin{array}{c}x\\ y\end{array}\right]=\left[\begin{array}{c}u_{0}\\ v_{0}\end{array}\right]+\left[\begin{array}{cc}c& d\\ e& 1\end{array}\right]\frac{R_{p}}{\left\|R_{p}\right\|}\cdot f(\theta)$$ |

### EUCM model



"model":"EUCM"

The Enhanced Unified Camera Model(see EUCM model.pdf) implementation is applicable to catadioptric systems and wide-angle fish-eye cameras.

### Parameter description



| Parameter | Possible values | Description |
| --- | --- | --- |
| principal_point | float[2] | Sets the principal point of the camera(in pixels). |
| focal_length | float[2] | Sets horizontal and vertical focal lengths in pixels. An array of two floats. |
| alpha | float | Expects a parameter between 0.0 and 1.0(inclusive). |
| beta | float | Expects a parameter greater than 0.0. |

### Camera output description

The simulator can capture a scene just like a real camera sensor. In addition to imagery data, it can also provide supplemental data assigned to each pixel, such as the distance from the sensor's plane or the segmentation class.

Below is the list of data that aiSim can export in image format:



| Data type | Description |
| --- | --- |
| LDR color data | ● Stored in 8-bit in gamma-compressed format in the sRGB color space ● The color data is tone-mapped and includes numerous artistic effects, such as"bloom" or"color correction" ● The color data can be three-channel(RGB), four-channel(RGBA), or one-channel in the case of Bayer-encoding |



| HDR color data | ● Stored in linear 32-bit float values in four-channel(RGBA) format in the sRGB color space |
| --- | --- |
| Distance(depth) data | ● Single-channel, 16 or 32-bit● Contains the distance from the camera plane in meters. Contains the distance from the camera plane in meters. ● The distance is stored in either 16-bit or 32-bit floating point values depending on the configuration. 。 The 16-bit float uses the IEEE 754 half-precision binary format. |
| Segmentation ID data | ● Single-channel,8-bit or 16-bit See parameter use_legacy_segmentation. • Contains the segmentation/classification data in the 0-65535 range(2 bytes). The classification label of a value is listed in the default_segmentation.json file.  You can find the default_segmentation.json under the following paths: o Windows:&LOCALAPPDATA%\aiMotive\toolchains\toc_core- \clients\data\segmentation_settings\default_segmentation.json o Ubuntu:/opt/aiMotive/toolchains/tc_core-/clients/data /segmentation_settings/default_segmentation.json |
| Sensor blockage ground truth | ● Single-channel,8-bit paletted image ● Contains a 1-byte GT data for the generated sensor blockage ° 0 means clean °85 means transparent °170 means semi-transparent  $\circ$  255 means opaque |
| ColorYUV | ● ColorYUVI420 ● ColorYUVNV12 ● ColorYUVYV12 |
| Object ID | ● Contains 32-bit integer object IDs, where 0 is the invalid object ID. By default the high-level object IDs are used, so,e.g., a vehicle has a uniform ID across all of its sub-meshes.  $\circ$  See also render_detailed_object_ids parameter in the Common input parameters for all camera models section above on this page. |

### Bounding boxes

The purpose of bounding boxes is to approximate an arbitrarily-shaped object with:

● a rectangle area

 o in case of axis-aligned bounding boxes,

● or a cuboid area

 o in case of oriented bounding boxes.

Axis-aligned bounding boxes are two-dimensional and they never rotate. They either expand or contract to accommodate the object's shape and size On the other hand, oriented bounding boxes are three-dimensional, and they have a fixed shape that travels with the object regardless of its position.The bounding box information provides sensor coordinate system data about the objects within the view of a camera.Enabling per-pixel occlusion calculation(occlusion_enabled) activates a rendering pipeline that can calculate the visibility of detected objects(up to 64) on an image.



Note the differences in coordinate systems in which output data is interpreted for different camera sensor output entities. See below in the B ounding box output description section.



### Input parameter

See the bounding_box_config JSON sub-group in the Common input parameters for all camera models table on this page for bounding box configuration.

### Bounding box output description

The output of the bounding box sensor can provide the following:

● 2D bounding boxes measurements, interpreted in the Image-Space Coordinate System.

° 2D bounding boxes are axis-aligned bounding boxes.

● 3D-oriented bounding boxes(as opposed to axis-aligned bounding boxes), interpreted in the camera sensor's own coordinate system.

3D bounding boxes are oriented bounding boxes.

● Velocities of detected objects, interpreted in the camera sensor's own coordinate system.

● Custom attributes of meshes added by the user.

° World space position, orientation

● Additional information available for traffic lights:

° World space position, orientation

 o Traffic light state

 o Individual signaling element states

 o Signal arrangement

 o Subject categories



 Traffic light output fields signals,arrangement, and subjects are only filled out if the map supports these values.



The sensor output description can be accessed by opening the index.html file in the aisim_sdk-<ver>/aisim_doc-<ver>/html/folder.

If you are looking for a sensor named SensorXYZ, please check the folders index.html aiSim Classes Class list aim sim sensors[sensorXYZ] interface, then look for subfolders describing sensor messages: they can be subfolders named e.g.:[sensorXYZ]Sensor,SensorCapture,[sensorXYZ]Object,[sensorXYZ].Object attribute units are specified for each attribute in those pages, if relevant.



An important difference between the origin of axis-aligned and oriented bounding boxes:

● The origin of axis-aligned bounding boxes is located in the top left corner of the rectangle.o which is the 0, 0 coordinate of the box.

● The origin of oriented bounding boxes is located in the center of the rectangular prism.

o which is the intersection point of the diagonals within the shape.

For better visualization, see the figures below.

### Figures for output messages



Note: Lane sensor visualization(last example image below) is available in the aiSim Client viewport but not in the aiSim GUI viewport.

The figures below help to understand certain sensor output messages.



2D bounding box parameters



2D bounding box origin(top left point of the box)



3D bounding box m_3d_extent



3D bounding box origin(center of the box)



3D bounding box from above



 Occlusion



Truncation



 An example image of the m_lane_separators message.

### Sensor output coordinate system

● Camera images are interpreted in the lmage space coordinate system.

● 2D bounding boxes are interpreted in the Image space coordinate system.

$$
\circ\text{ For 2D bounding boxes, the origin is the top-left corner in normalized image space(0..1).}
$$

● 3D bounding boxes are interpreted in the camera sensor's own coordinate system.

For 3D bounding boxes, the origin is defined as the center of the box.

● Velocities of detected objects are interpreted in the camera sensor's own coordinate system.

### Camera graphics and realism parameters

On this page, we summarize different configurations and parameters that affect the visual quality and the degree of realism in aiSim. These parameters can determine how realistic aiSim's graphics are and thus influence the perception of camera sensors. Enabling certain graphical features may have an effect on aiSim's performance.

In aiSim, graphics and camera realism can be controlled by the following configurations:

● The camera-specific input parameters of the sensor configuration,

Global performance parameters,

### Table of Contents:

•Screen Space Ambient

 Occlusion(SSAO)

●Lens flare

 Chromatic aberration

 Depth of Field(DoF)

Motion blur

 Draw distance

 Color grading

 Bloom

 Tone mapping

 Color correction effects

 Reflection planes

 Cascaded shadows

 Shadow pool resolution

 SkyVisibility/AmbientOcclusion for maps

●Sensor blockage

● Ray-tracing camera

 Denoising and fine tuning ray-tracing images

 Setting Region of Interest(ROl) for ray-tracing cameras

● Graphical assets● Sun phantom in road traffic

● Graphical assets● Sun phantom in road traffic Sun phantom in road traffic lights

● Camera distortion models

 Cube_6_Face

 Single image

 Configuring the

 camera render

 parameters

### Anti-aliasing(AA)

 Aliasing happens when a curved line is drawn across square pixels: rendered triangles become discrete pixels during rasterization, which causes jagge d edges at the edges of triangles.

aiSim offers the following anti-aliasing techniques:



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| SMAA | Low | Camera sensors | "render_p roperties ":{ "smaa _enabled" :true, } | SMAA provides additional edge smoothing on the image by using edge detection and selective blur. ● SMAA only blurs edges detected on the image; it does not add new information ● Works well for large-resolution sensors |



| $$\text{Supersampling}$$ | High | Camera sensors | "render p roperties ":{ "su persampli ng_enable d": true, } | Supersampling is achieved by rendering the image at double the resolution (Supersampling 4x) of the one being displayed, then shrinking it to the desired size using the extra pixels for calculation. The result is a downsampled image with smoother transitions from one line of pixels to another along the edges of objects. ● Renders four times the resolution internally(four samples per pixel) ● Provides the best-quality image A Supersampling is not supported for ray-tracing cameras |
| --- | --- | --- | --- | --- |
| $$\text{Supersampling}$$ | High | Camera sensors | "render p roperties ":{ "su persampli ng_enable d": true, } | You may increase the samples_per_pixel parameter instead of using Supersampling for ray-tracing cameras for a similar result |



### Screen Space Ambient Occlusion(SSAO)

Screen Space Ambient Occlusion(SSAO) is a technique for efficiently approximating the ambient occlusion effect in real-time. Ambient occlusion is the point at which an object stops light from a source, as well as the point at which an object throws light or shadow in its created world.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| SSAO sampling | 64=Medium | Camera sensors | "render_properti es":{ "ssao_sample s":64, } | This parameter sets the number of sampling |
| SSAO intensity and radius | Low | Environmental presets and configuration | $$\{\quad$$ "post_process": { "ao_intensity": 0.5, "ao_radius": 0.25 }, $$\cdots$$ | Sets the intensity of the ambient occlusion calculations Sets the radius from the surfaces in which the ambient occlusion is calculated. Expressed in meters. |





### Lens flare

A lens flare happens when light is scattered or flared in a lens system, often in response to bright light, producing a sometimes undesirable artifact in the image.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Lens flare | Low | Camera sensors | "render_properties" :{ "lens_flare_int ensity":0.0001, \} | The lens flare is visible only when the sun is directly visible in the camera's field of view. The lens flare effect intensity value is expressed as a percentage of the sun's intensity. For precise calibration of the lens flare effect, see the lens_flare _intensity parameter on the Camera sensors page. |



### Chromatic aberration

Chromatic aberration is a color distortion that creates an outline of unwanted color along the edges of objects in a photograph



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Chromatic aberration | Low | Camera sensors | "chromatic aberration _type":"STN", "chromatic_aberrati on_parameters":{ "red_channel_tran slation":[ 0.004, 0.007], "green_channel_tr anslation":[ 0.005, 0.006], "blue channel_tra nslation":[ 0.006, -5.052e-5], "green_channel_sc ale": 0.999 }, | $$\text{ STN model uses the translation to each color channel of an image in}$$ 2D pixel space and the scaling of the green color channel relative to the red and blue channels. You can also define the translation of each color channel and the scaling of the green channel. |



### $$\text{ Depth of Field(DoF)}$$

The depth of field(DoF) is the distance between the nearest and the furthest objects that are in acceptably sharp focus in an image captured with a camera.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Depth of Field | Low to high based on parametrization | Camera sensors | "camera_config":{ "dof_parameters": { "focus_distance": 1e6, "aperture_diameter": 0.01, "sensor_size_scaling_numb er": 4e-6 }, | See the following page for detailed parameter and configuration information: Depth of Field simulation. |
| --- | --- | --- | --- | --- |



|  |  |
| --- | --- |
|  |  |
| DoF parameters: "focus_distance": 10, "aperture diameter": 0.07 | DoF parameters: "focus_distance":70, "aperture_diameter": 0.07 |
|  | DoF disabled |
|  | DoF disabled |
| DoF parameters: "focus_distance": 100, "aperture_diameter": 0.01 | DoF disabled |

### Motion blur

Motion blur is the apparent streaking of moving objects in a sequence of frames.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Motion blur | Low | Camera sensors | "camera config ":{ "motion_bl ur_enabled": true, "max_motion_bl ur_samples": 16, | $$\text{ In aiSim, motion blur is achieved by considering the per-object movements. For this,}$$ the render engine creates a velocity map(a buffer) to determine the extent of blur and the direction. Limitation ● Motion blur is enabled only if velocity_type is set to OpticalFl ow. ● Motion blur is not supported if ray tracing is enabled. |

Click to play a motion blur comparison video:



### Draw distance

Draw distance is the maximum distance of objects in a three-dimensional scene that is drawn by the rendering engine. Polygons that lie beyond the draw distance will not be drawn.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Draw distance | Low to high based on distance | Camera sensors | "render_p roperties ":{ "near _plane": 0.01, "far_plan e": 1024.0, } | Draw distance can be controlled by the near plane and far plane parameters; The camera renders the area between the near plane and the far plane; in meters. The higher the far plane, the higher the impact on the performance |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

### Color grading

Color grading is a process that maps the sensor output color to a different color based on a lookup table.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Color grading | Low | Camera sensors | "render_properties":{ "post_process_render_parame ters":{ "color_grading_lut_uri" me>" $$\begin{array}{l}:\\ \text{"://"}\end{array}$$ } | The URI points to a CUBE file or 3D DDS texture file containing a color mapping LUT. LUT files are useful for color grading, encapsulating complex color-space transforms, or emulating film stock for photography and video. |

### Bloom

Bloom is used to reproduce an imaging artifact of real-world cameras. The effect produces fringes(or feathers) of light extending from the borders of bright areas in an image, contributing to the illusion of an extremely bright light overwhelming the camera capturing the scene.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Bloom | Low | Camera sensors | "render pro perties":{ "max_bl oom_depth": 4, "post_p rocess_rend er_paramete rs":{ "bloom_inte nsity": 0.04, "use_bloom firefly_fil ter": true, } } | ● bloom_intensity: Sets the strength of the bloom effect by a percentage(between 0.0 and 1.0) of the applied bloom effect and the original color. ● use_bloom_firefly_filter: Enables a firefilter filter for reducing small but very bright artifacts. If enabled, the bloom effect is slightly decreased. max_bloom_depth: Set the"ring" size of the bloom by configuring the desired lowest MIP-level for the bloom algorithm. For example, in the case of a FullHD camera, level 4 is 67p(540p>270p>135p>75p).The lowest the level, the bigger the bloom ring. |
| --- | --- | --- | --- | --- |



### $$\text{Tone mapping}$$

$$\text{Tone mapping is a technique used to map one set of colors to another to approximate the appearance of high-dynamic-range images in a medium}$$with a more limited dynamic range. aiSim generates HDR images containing the physical light values in the range 0.0-inf. With tone mapping, you can map light values into the range 0.0-1.0.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Tone mapping | Low | Camera sensors | "render_properties":{ "post_process_render_para meters":{ "tonemapper": "FilmicACES", } \} | Possible preset values: Filmic; FilmicACES; Reinhard; AMDFidelityFXLPM; Linear; A custom tone mapper can be implemented by exporting the raw HDR image. |



### Color correction effects

### Contrast

Contrast pushes color values to their extremes, making darks darker and lights lighter. aiSim's contrast solution incorporates contrast and its opposite, similitude. A 0 contrast value shifts every color value to achieve 100% similitude achieving a uniform mid-tone grey look. A 1 contrast value leaves the color values as they are. And a contrast value 2 pushes every color value to its respective minimum or maximum, flooding the image with the darkest and lightest values. To differentiate between light and dark values, the algorithm also uses a contrast_center parameter. By default, the contrast center is set to 0.5, meaning that the lower half of color values in the image is considered dark, while the upper half of the image is considered light. A contrast center value 0 means that every color value is considered light and none dark. A contrast center value considers every color value as dark and applies contrast to the image this way.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Contrast | $$\text{ No impact}$$ | Camera sensors | "render prop erties":{ "post_proces s_render_par ameters":{ "contrast": 1.0, "contrast_ce nter": 0.5, } | $$\text{ Default values, contrast}=1\text{ and contrast center}=0.5\text{, leave the image}$$ unchanged. Lowering the contrast_center value from 0.5 with a contrast value higher than 1 shifts more colors to be brighter and vice-versa. |
| --- | --- | --- | --- | --- |

Example images with different contrast and contrast_center parameter values:





For more post-process effects, see the following parameters on the Camera sensors page:

sharpen_strength

 sharpen_limit

•color_temperature

•saturation

•white_multiplier



 Post-process effects do not affect performance.

### Reflection planes

Enables an extra rendering step for vehicle chassis to be visible in reflections along with shadows under vehicles.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Reflection planes | Medium | Performance management | { "enable_reflection_planes": true, \} | Only relevant in rainy or very foggy environments. |
| --- | --- | --- | --- | --- |



### Cascaded shadows

Cascaded shadows control the shadow maps generated for the Sun.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Cascaded shadows | $$\text{ Low to high based on}$$ parametrization. | Performance management | { | $$\text{ See Shadow Pool Resolution on this page for}$$ shadows by artificial light sources |
| --- | --- | --- | --- | --- |
|  | This feature demands high V- RAM. |  | "cascaded_shadow_blend" :true, "cascaded_shadow_resolut ion":2048, } |  |



### Shadow pool resolution

Shadow pool resolution controls the shadow maps generated for artificial light sources.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Shadow pool resolution | Low to high based on parametrization This feature demands high V- RAM. | Performance management | { "shadow_pool_resolutio n": 4096, | See Cascaded Shadows on this page for shadow maps generated for the Sun. |



### SkyVisibility/AmbientOcclusion for maps

SkyVisibility is understood in terms of values arranged in a 3D grid, ranging from total exposure to total occlusion. AmbientOcclusion is a shading and rendering technique used to calculate how exposed each point in a scene is to ambient lighting. These are lookup tables with precalculated lighting parameters in a 3D texture. With this parameter, the use of these textures is switched on or off.

Supported maps:

●Budapest_Urban

 US_Urban

 Demo_Loop

 All environment editor minimaps



 Available for raster graphics.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| SkyVisibility /AmbientOcclusion | Medium | Performance management | { "allow_sv_ao_maps": true, } | Applied to dynamic geometry(e.g., cars) as well. Only for supported maps. See Performance management. |



### Sensor blockage

aiSim can simulate contamination that appears on the camera lenses.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Sensor blockage | Low | Camera sensors | "sensor_blockage_parame ters":{ "type": "Condensation", "bias": 33.0, "seed": 2547, "generate_gt": true }, | See the following page for detailed parameter and configuration information: Sensor blockage and contamination |
| --- | --- | --- | --- | --- |



"type":"Condensation"



"type":"Mud"

### Ray-tracing camera

Ray-tracing is a graphics rendering method that simulates light's physical behavior. Ray tracing works by tracing the path of rays of light as they bounce off objects in the simulated scene and eventually reach the camera sensor. The more rays that are traced, the more accurate the image will be, but also the longer it will take to render.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |
| Ray- tracing | High | Camera sensors | "render_properties":{ "is_ray_tracer": true, "raytrace_properties": { "enable_accumulation": true, "maximum_distance": 1024.0, "sky_and_sun_lighting_ samples":8, "samples_per_pixel": 1, "light_samples": 10, "use_firefly_filter": true, "denoiser_type": "HighQuality", "secondary_bounces_typ e": "SpecularAndDiffuse" \} | See the following page for detailed parameter and configuration information: Camera sensors. The Nvidia RTX video card series support ray-tracing cameras. Non-RTX Video cards do not have native raytracing capabilities. Although they can emulate the ray-tracing functionality to some level, it is insufficient for ray- tracing sensor simulation. Limitations with ray-tracing cameras Ray-tracing cameras have a limited feature set compared to non-ray- tracing cameras. The following limitations are in effect if ray tracing is enabled: ● Motion blur is not supported ● Velocity output: parameter velocity_type must be set to None supersampling_enabled must be set to false. You may use samples_per_pixel instead of supersampling for ray-tracing cameras for a similar result. |





### Denoising and fine-tuning ray-tracing images

The following techniques are available for denoising and fine-tuning ray-tracing image quality.



All techniques below are deterministic.



CTRL+ click on the links in bold to open the sample images in a new tab.



| "samples_per_pixel": 50 "secondary_bounces_type": Specular "use_firefly_filter": false "denoiser_type":"None" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": true "denoiser_type":" HighQualit y" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": true "denoiser_type":"LowQuality" Screenshot | $$"_{\text{samples\_per\_pixel": 50}}$$ "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": true "denoiser_type":"None" Screenshot |
| --- | --- | --- | --- |
| "samples_per_pixel": 50 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": false "denoiser_type": " HighQualit y" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": false "denoiser_type": "LowQuality" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": false "denoiser_type":"None" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": Specular "use_firefly_filter": false "denoiser_type":"None" Screenshot |
| "samples_per_pixel": 1 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": true "denoiser_type":" HighQualit y" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": true "denoiser_type":"LowQuality" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": true "denoiser_type":"None" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": false "denoiser_type":" HighQualit Screenshot |
| "samples_per_pixel": 1 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": false "denoiser_type":"LowQuality" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": "SpecularAndDiffuse" "use_firefly_filter": false "denoiser_type":"None" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": Specular "use _firefly_filter": true "denoiser_type":"LowQuality" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": Specular "use_firefly_filter": true "denoiser_type":"None" Screenshot |
| "samples_per_pixel": 50 "secondary_bounces_type": Specular "use_firefly_filter": false "denoiser_type":" HighQualit y" Screenshot | "samples_per_pixel": 50 "secondary_bounces_type": Specular "use_firefly_filter": false "denoiser_type": "LowQuality" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": Specular "use_firefly_filter": true "denoiser_type":"LowQuality" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": Specular "use_firefly_filter": true "denoiser_type":"None" Screenshot |
| "samples_per_pixel": 1 "secondary_bounces_type": Specular "use_firefly_filter": false "denoiser_type": " HighQualit y" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": Specular "use_firefly_filter": false "denoiser_type":"LowQuality" Screenshot | "samples_per_pixel": 1 "secondary_bounces_type": Specular "use_firefly_filter": true "denoiser_type":" HighQualit y" Screenshot |  $-$  |

### Setting Region of Interest(ROI) for ray-tracing cameras

You can achieve potential performance improvement for ray-tracing cameras in those use cases where rendering the full-size image is not required.The regions-defined as a list of rectangles in the image space-represent parts of the image that the user is interested in. Parts of the image outside the regions are rendered at a downscaled resolution or not rendered at all.



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



### Denoising of ROI

Denoising runs on the defined regions of interest only. If you defined more ROls, denoising will run in the smallest bounding rectangle.Example:



Orange rectangles: two regions of interest Yellow rectangle: effective region for denoising(bounding rectangle)Outside area: noisy area

### Graphical assets

 By default, aiSim uses the following material data for custom graphical assets:

Albedo: contains the intrinsic color of the surface

● Albedo: contains the intrinsic color of the surface● Normal map: contains detailed geometric details

● Albedo: contains the intrinsic color of the surface● Normal map: contains detailed geometric details● Roughness/metallic map: contains surface roughness and metalness values





No Normal map



 No Roughness map



### Sun phantom in road traffic lights

Sun phantom(also known as ghost sign) is a spurious signal indication caused by the sunlight at the optical surfaces of traffic signal assemblies.Currently, the reflection of the paraboloid mirror(reflector) of the incandescent lamp is approximated by 10% of the sunlight. The rendering engine of aiSim simulates the sun phantom effect by default. It is not possible to disable or configure the sun phantom effect.



For more information, refer to B. L. Cole and B. Brown. An Analysis of Sun Phantom in Road Traffic Signal Lights. Journal of the Australian Road Research Board, Vol.3,No.10,1969.

### Camera distortion models

Distortion models describe the mathematical deviation of a camera from the pinhole model.

Camera sensor rendering starts by rendering pre-distortion rendering images. These images use regular perspective projection and provide data(color, segmentation, etc.) for the distortion algorithms and thus for the final camera sensor image.

Pre-distortion rendering images can be, for instance, a single image("environment_mapping_type":"None") or a total of six images("environ nment_mapping_type":"Cube_6_Face"), depending on the characteristics of the simulated camera model.The environment_mapping_type parameter has the following options for the automatic selection of environment mapping:



### Cube_6_Face

In this method, aiSim renders six images in each frame where each image is a side of a cube:



Next, aiSim calculates camera model coefficients, applies render parameters, then converts the 2D image to 3D by using a 3D ray LUT to get the final image:





● The 3D ray LUT is an R32G32B32A32_FLOAT DDS image file. An example python script to generate DDS LUT files is available in the aiSim SDK package here:aisim_sdk-<ver>Release<OS>/aiSim_sdk-<version>Release<OS>/aisim-<version>/tools/generate aimdistortion lut.py

### Single image

 In this method, aiSim renders one image in each frame. It is the recommended method if the Camera FoV is lower than 120°:



### Configuring the camera render parameters



| Name | Impact on performance | Place of Configuration | Configuration | Description |
| --- | --- | --- | --- | --- |



| Cube_6_Face | Low to high based on parametrization | Camera sensors | "render_p roperties  { "environm ent_mappi ng_type": "Cube_6_F ace", } | If the sensor has a FoV larger than 120°, then Cube 6 Face mapping type is recommended i Cube_ 6 Face mapping type covers the entire FoV; therefore, there's no need to set FoV. |
| --- | --- | --- | --- | --- |
| Single image("None") | Low to high based on parametrization | Camera sensors | "render_p roperties ": { "environm ent_mappi ng_type": "None", } | If the sensor has a lower FoV, a single pre-distortion image is recommended with a large enough FoV to provide enough data, but not too large. |
| render_y_fov | Low to high based on parametrization | Camera sensors | "render_p roperties ": { "render_y fov" : 90.0", } | If the environment mapping type is set to a single image(None), this parameter controls the FoV of the single internal image. |
| render_resolution_per_face | Low to high based on parametrization | Camera sensors | "render_p roperties ": { "render_r esolution _per_face ":512", } | This parameter controls the resolution of the internal(pre-distortion) images It should be chosen carefully depending on the camera distortion model since it has a direct impact on the final image quality. Too low of a value can lead to loss of detail, while too high a value can cause unnecessarily low rendering performance. We recommend that you set the environment_mapping_type to one of the Auto_* option to let the program calculate the optimal render_resolution_ per_face. |



See all the available camera distortion models on the following page: Camera sensors

### Camera exposure control

In aiSim, the exposure value is used to set the ideal brightness of images. Exposure value helps transition content from the high dynamic range to the low dynamic range. Exposure calculation is applied to each channel of the RGB, and the calculation is carried out before the tone mapping.

To configure the method for controlling camera exposure, use the type parameter(under camera_exposure_control). For more information on usage,see the descriptions on page Camera sensors.

aiSim supports the following methods for setting up camera exposure values:

### Automatic camera exposure

Automatic camera exposure adjusts settings automatically to achieve a well-balanced image brightness based on the scene's lighting conditions dynamically.



If automatic camera exposure is selected, the shutter_speed, f-stop, and sensitivity parameters in a sensor configuration are not taken into consideration by the system.

### Method 1: Via calculating average luminance

In this method, aiSim takes the average luminance of the light captured by the camera to set camera exposure value. Because of this, this method works independently of the image resolution and the current environmental configuration.

To enable automatic camera exposure, set the type parameter(under camera_exposure_control) to AutoFromAverageLuminance in the sensor configuration file.



See also optional related parameters for fine-tuning the automatic camera exposure on page Camera sensors:

● auto_exposure_luminance_key_value

●auto_exposure_luminance_min

●auto_exposure_luminance_max



 For more information on the parameters and the implementation, see the following article:https://knarkowicz.wordpress.com/2016/01/09/automatic-exposure/

### Method 2: Via LUT

In this method, aiSim uses lux-exposure value pairs in ascending order, without a cardinality limit. This array is described in the sensor configuration JSON file. The exposure value to an unknown lux value can be linearly interpolated or constrained to the closest value.

To enable automatic camera exposure, follow the steps:

1. Set the type parameter(under camera_exposure_control) to AutoFromExposureLUT in the sensor configuration file.

2. Define increments for lux key values using the lux_increment_for_lut_keys parameter.

The increment of lux key values assigned to each exposure value in the auto_exposure_lut starts from 0.0.

E.g.:In the case of 1000.0 increment, the key-value pairs are:0.0-0.005,1000.0-0.001,2000.0-0.0005,3000.0-0.0003...

3. Fill in the auto_exposure_lut LUT in the sensor configuration file.

"camera_exposure_control":{"type":"AutoFromExposureLUT","lux_increment_for_lut_keys": 1000.0,"auto_exposure_lut":[0.005,0.001,0.0005,0.000333333,0.00025,0.0002,0.000166667,0.000142857,0.000125,0.000111111,0.0001



Lux is calculated aiSim-internally. In challenging high dynamic range situations(such as Sunny outdoor weather), you must set the enable_flo at 32_hdr value to True(32bit). Read more about it on the Performance management page.



Autoexposure works by calculating the average lux values of the image. Due to the nature of how the raytracing camera works, low sample counts can cause a noisy image, meaning a large variation of lux values between frames can result in flashing images when automatic camera exposure is used. To mitigate this, consider increasing the value of samples_per_pixel for the camera sensor and enabling image denoising along with the Firefly filter.



### Limitations

You can set automatic camera exposure individually for each camera.

The Pinhole, Fisheye, and Mei camera models work reliably with automatic camera exposure.

AMDFidelityFXLPM tone mapper is not supported.

### Manual camera exposure

The exposure value is calculated by an algorithm by supplying the following three parameters manually:

● F-stop

 Shutter speed

 Sensitivity(ISO)

The parameters above can be configured in two places:

1. Editing the parameters for a camera in a sensor configuration file.

We suggest this method if you want to set different manual exposure settings for each camera in your sensor configuration.

a. Set the type parameter(under camera_exposure_control) to ManualFromSensorConfiguration.



b. Fill in the parameters in the global_camera_exposure_parameters JSON array in the sensor configuration file for a camera sensor.2. Editing the Environmental configuration file that later can be used for several camera sensors in a sensor configuration file.

We suggest this method if you want the same manual exposure settings for several cameras in your sensor configuration.

Example:

a. Set the type parameter(under camera_exposure_control) to ManualFromEnvironmentConfiguration for each camera sensor in your sensor configuration.

"camera_exposure_control":{"type":"ManualFromEnvironmentConfiguration",\},

b. Fill in the parameters in the camera exposure parameters JSON array in the Environmental configuration file.

### $$\text{Depth of Field simulation}$$

The depth of field(DoF) is the distance between the nearest and the furthest objects that are in acceptably sharp focus in an image captured with a camera. DoF is a property of the camera lens system(hereinafter'camera lens') that affects the perception of shapes. aiSim's approach to DoF effect simulation is based on the per-pixel calculation of the circle of confusion, for which we implemented the thin lens model.

### Supported camera models

OpenCV pinhole model

 OpenCV fisheye model

● Perspective model



 DoF enabled for an OpenCV pinhole camera

 To configure DoF simulation, add the following JSON object to your sensor configuration:

"sensors":{"front_left":{"type":"camera","update_intervals":[40000],"camera_config":{"dof_parameters":{"focus_distance": 1e6,"aperture diameter": 0.01,"sensor_size_scaling_number": 4e-6$$},\\ \\ \end{array}$$ $\cdots$ 

### Parameter description



| Parameter | Parameter | Type | Explanation |
| --- | --- | --- | --- |
| dof para mete rs |  | JSON sub- group | Contains parameters for the Depth of Field effect. |
|  | focus_dis tance | float or string | Sets the camera lens' focus distance, in meters. Setting the infinity string as a parameter value sets the focus to infinite distance. |
|  | aperture diameter | float | Sets the camera lens' aperture diameter, in meters; zero value disables DoF. |



|  | $$\text{ sensor}_{\text{ze}}\text{ scalin}$$ $$\text{ ze scalin}$$ g_number | float | The algorithm behind the DoF effect requires the approximate physical size of the camera's imager sensor. This is calculated by the hei ght parameter of the camera sensor and this sensor size scaling number parameter. The sensor size scaling number value correlates with the imager cell's physical size, which is typically 4 microns |
| --- | --- | --- | --- |

### Segmentation images, semantic labels, custom attributes

Segmentation neural networks(NN) can partition the image into semantically meaningful parts and classify each part into one of the pre-determined classes. In aiSim, you can generate segmentation images using camera sensors. In computer vision, image segmentation is the process of dividing an image into multiple segments or regions based on certain characteristics.

### Segmentation images

The segmentation images are made of unicolor shapes that represent the segmentation IDs of visible objects based on their semantic labels. The image is calculated by the aiSim's engine based on the semantic label information. This information is available for each map's map.json file about all the visible objects.



Segmentation image



 To enable the segmentation images, refer to the segmentation_enabled parameter for the camera sensor.To control how segmentation images are exported, refer to Exporting sensor data.

### Semantic labels

Semantic labels are descriptive tags assigned to content elements that distinguish and specify their meaning. They specify how detection algorithms categorize objects. Semantic labels are assigned to meshes that build up objects. Sensors can access and read semantic labels assigned to meshes. In aiSim, 20+ unique semantic labels can be assigned to meshes



 You can change or extend semantic labels with new ones in the aiSim Unreal Editor(refer to Asset semantic labels for more information).

You can find an example segmentation settings file in the following location.:

● aisim_gui-<ver>\data\default_segmentation.json

●toolchains\tc_core-<ver>\clients\data\segmentation_settings\default_segmentation.json

 Each segmentation setting entry consists of the following information:

● aiSim semantic label

● aiSim segmentation ID

● color codes in RGBA format

● LiDAR(LAS) classification codes

"sky_segmentation_semantic_label":"MySky","segmentation_settings":[\{"semantic_label":"Road","segmentation_id":0,"color":{"r":74,"g":163,"b":39,"a":255},"las_type":11},"semantic_label":"MySky","segmentation_id":1,"color":{"r":115,"g":162,"b":170,"a":255},"las_type": 0},{"semantic_label":"Building","segmentation_id":2,"color":{"r":209,"g": 126,"b":59,"a":255},"las_type":6

### Change in aiSim v5.6.0 and up

In aiSim v5.6.0, there is a new parameter named sky_segmentation_semantic_label. You can specify the expected label for the sky, this way you can give a custom semantic label for your sky segmentation. If the sky_segmentation_semantic_label parameter is not specified, aiSim uses the default Sky label. Having a semantic label block entry for the sky is mandatory.

### $$\text{Segmentation IDs}$$

Segmentation IDs are unique integers ranging from 0 to 65535 connected to semantic labels. You can use 8-bit or 16-bit segmentation IDs. Using 16-bit segmentation IDs allows the segmentation settings to define 65536 unique IDs as opposed to the 256 legacy 8-bit IDs.

To use the 16-bit segmentation IDs, set the use_legacy_segmentation field in the camera's sensor configuration JSON to false.

Segmentation IDs can be customized in default_segmentation.json file.

You can then apply your customized segmentation settings through the simulation client(e.g., via the--segmentation_settings_path argument in the aisim_client).

If you start the simulation via the aiSim GUI, overwrite the following file to apply your custom segmentation settings:

● Windows:%LOCALAPPDATA%\aiMotive\aisim-gui-<aiSim_version>\data\default_segmentation.json

● Ubuntu:/opt/aiMotive/aisim_gui-<aiSim_version>/data/default_segmentation.json



Multiple semantic labels can have the same segmentation ID.



To learn how to separate a motorcycle and the rider for segmentation tasks, refer to the following page: Vehicles

### Custom attributes

 Beyond semantic labels, you can also use custom attributes for meshes. Custom attributes are metadata for sensors or custom data for categorizing assets.



Refer to the following guide for more information: Adding custom attributes to static meshes

### Custom tags

 Custom tags are tags you can assign to actors and vehicles to add any additional information in the form of a string. In the case of vehicles, they can be accessed from the vehicle's actor JSON file, and in the case of map actors, they can be accessed from the map's JSON file. One actor or vehicle can have multiple tags associated with it.

To assign custom tags to map actors refer to the Adding custom tags to actors page and to add them to vehicles see the Custom asset tags for vehicles page.

### Sensor blockage and contamination

This page describes how to set up sensor blockage that affects how a sensor perceives the simulated environment.

### Camera sensor blockage

aiSim can simulate contamination that appears on the camera lenses. To add blockage to camera sensors, add the following block to your camera sensor's configuration JSON:

"sensors":{"pinhole":{"type":"camera""visibility_mask_gt_flags":["SensorBlockage"]"sensor_blockage_parameters":{"type":"Condensation","bias":33.0,"seed":2547,},}}

### Parameter description



| Parameter | Possible values | Explanation |
| --- | --- | --- |
| visibility_mask _gt_flags | array of strings | Enables generating visibility mask ground truth images of a contaminated camera sensor. Values: ● SensorBlockage: Applies mud or condensation(see type below) ● Atmosphere: Applies fog ● Precipitation: Applies rain or snow You can add more than one value for a combined effect, for example,"visibility_mask_gt_flags":[ "Precipitation","SensorBlockage"]. To enable sensor image export, add visibility_mask_gt as a subtype to your sensor export configuration. See Exporting sensor data. |
| sensor_blockage parameters | JSON sub- block | Specifies the sensor blockage parameters. |
| type | string | Sets the type of contamination. Possible values: Condensation; Mud |
| bias | float | Increases the contamination that covers sensor lenses. Range:(0-100) where 0 is the base contamination, 100 is fully contaminated. The contamination extends radially for Condensation. |
| seed | int | Provides seed for random number generation. Range: 0-INT_MAX |

### Examples

### 1.

"visibility_mask_gt_flags":["Atmosphere","Precipitation","SensorBlockage"],"sensor_blockage_parameters":{"type":"Mud","bias": 11.2,"seed": 250





2.

"sensor_blockage_parameters":{"type":"Condensation","bias": 45.2,"seed":326,},



3.





4.

"sensor_blockage_parameters":{"type":"Condensation","bias": 90.2,"seed": 326,},



5.





### Accessing luminance from camera sensors

### Introduction

The goal of aiSim is to simulate all lighting correctly and physically plausible in a high dynamic range. To achieve this, aiSim uses the rendering equation,which is a fundamental concept in computer graphics that describes the interaction of light in a scene. The result of the lighting simulation is HDR lighting data that is stored in an intermediary memory.

To ensure an interactive framerate, aiSim's rendering engine simplifies the equation while keeping the unit of measurement: luminance values in the sRGB color space(linear values in high dynamic range).

### HDR lighting data format

In aiSim, HDR lighting data is represented in a 16-bit float RGB-triplet by default. You can also change to a 32-bit float format with the enable_float32_h dr performance parameter.



|  | Pros | Cons |
| --- | --- | --- |
| 16-bit float | ● More speed ● Uses less VRAM | ● Largest value:6.55 x104 ● Decimal digits of precision: 3.31 |
| 32-bit float | ● Largest value: 3.4028237 x 1038 ● Decimal digits of precision: 7.22 | ● Less speed ● Uses more VRAM |



We recommend 16-bit floats for speed-critical simulations and saving VRAM, while 32-bit floats provide the best data precision.

### Exporting HDR lighting data

aiSim can export HDR lighting data in EXR(default) and DDS file formats. See more at Exporting sensor data. The exported HDR data is always converted to a 32-bit float, irrespective of the HDR lighting data format. Out of the four channels, the alpha channel already contains an illuminance incident on the surface(unit: lux).



To calculate luminance from the exported data, you can also apply colorspace conversion on the RGB-triplets: from sRGB to CIE XYZ. After converting to CIE XYZ, the value"Y" is luminance(unit: candela/m2).

### Limitations

The following limitations are in effect regarding HDR export:

Post-process effects(see post_process_render_parameters) do not take effect.

"Condensation" sensor blockage is not visible.

SMAA anti-aliasing is not available.

Depth of field is not available.

Lens flare is not available.

Exposure control is not available.

Chromatic aberration is not available.

### $$\text{Raw camera sensor output}$$

The raw camera sensor output emulates the signal process flow of a camera sensor, before applying an ISP component to the image. This enables users to configure a camera sensor's low-level parameters, achieving a more realistic camera simulation for, e.g., HiL applications. The raw camera sensor output works by rendering an RGBIrradiance image and applying configurable effects to it.

To enable raw camera sensor output, set the following sensor configuration parameter for the camera sensor:

"image_type":"AimRawCFA16"

The output is a 16-bit raw sensor data using a color filter array(CFA).

Supported export formats:.dat,.dds,.npy,.png,.tga

 Both raster-based and raytrace-based sensors are supported.

### Parameters

The raw camera sensor output can be configured in the standard sensor configuration by adding the parameters under the dynamic_image_sensor_par ameters.



| Parameter | Parameter | Type | Description |
| --- | --- | --- | --- |
| dynamic_imag e_sensor_par ameters |  | JSON sub- group | Configures the raw camera sensor output. |
|  | rgb_radiant_ exposure_to_ voltage | float[3] | Emulates how CMOS/CCD sensors convert incoming radiant exposure into voltage. aiSim calculates this value as follows: photon_energy  $=\frac{h c}{\lambda}$  $$\text{radiant_exposure_to_voltage}=\frac{\text{pixel_size}^2}{\text{phoron_energy}}$$ $$\frac{\text{ plxel_size}^{2}}{\text{ photon_energy}}\cdot\text{ quantum_efficiency}\cdot\text{ conversion_gain}$$ where: ● pixel_size: The physical size of a pixel on the sensor, expressed in meters - h: Planck constant ● c: The speed of light, expressed in m/s -: The wavelength of each channel of the RGB, expressed in meters quantum_efficiency: The quantum efficiency assigned to the wavelength of each channel of the RGB conversion_gain: The sensor's conversion rate expressed in Volts/electron. Sets the voltage generated by a single electron. |
|  | analog_gain | float | Analog signal gain, outgoing from the CMOS/CCD sensor. Multiplier. |
|  | voltage_swing | float | Sets the maximum voltage that the sensor may output. |
|  | adc_bit_prec ision | int | Sets the bit-depth for the analog-digital conversion. |
|  | digital_clamp | int[2] | Clamps the digital signal between two values. |
|  | digital_gain | float | This is a simple multiplier to the final camera output, before quantization. This property affects all non-HDR image types. Value range: 0.0-inf. The typical range of value is 0.5-2.0. |
|  | pre_pwl_pede stal | int | An offset before the PWL-based(Piecewise Linear function) companding. |
|  | pwl_control_ points | int[2] | The Piecewise Linear function(PWL) compresses the digital signal to a new value based on a pre-set curve. The curve can be adjusted with control points(max. 17), where a point's X value denotes the incoming digital signal, and Y value denotes the assigned compression value. |
|  | post_pwl_ped estal | int | An offset after the PWL-based companding. |

### Camera performance optimization

### $$\text{Real-time simulation with raytracing cameras}$$

Achieving real-time simulation with several raytracing cameras can be challenging, even with high-performance CPUs and GPUs. In this chapter, we have collected a few camera parameters to optimize performance without sacrificing image quality. For detailed parameter descriptions, see Camera sensors$$\text{ and Camera graphics and realism parameters.}$$



The sensors' update interval, which is how often a sensor delivers messages in a given time period, also affects the simulation's performance See more on Simulation scheduling.

First, we suggest that you test with the following raytrace_properties parameters, which will result in a high-performing simulation:



| Parameter | Recommended value |
| --- | --- |
| samples_per_pixel | 1 |
| light_samples | 1 |
| sky_and_sun_lighting_samples | 1 |
| denoiser_type | LowQuality |
| max_depth | 2 |



The settings above affect image sharpness, causing some lack of clarity, but should still provide reasonable image quality on smaller screens

 If you still experience real-time simulation performance issues, try also setting the following parameters:



| Parameter | Recommended value |
| --- | --- |
| use_firefly_filter | false |
| ssao_samples | 6 |
| internal_resolution_scale | Half |

