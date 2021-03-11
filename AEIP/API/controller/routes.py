from flask import Blueprint, request, Response, render_template
from model.sa1_aeip import TABLE_NAME, NAME_FIELD, SA1_LOC_INFO, SA1_BULD_EXPO, SA1_SEIFA, SA1_DEMO, SA1_ECON, \
                           SA1_INST, SA1_TRANSPORT, SA1_UTILITY, SA1_BUSINESS, SA1_AGRI, SA1_ENVI
from pyldapi import ContainerRenderer
import conf
import ast
import folium
import os, yaml

print(__name__)
routes = Blueprint('controller', __name__)

DEFAULT_ITEMS_PER_PAGE=50

# @routes.route('/fsdf_home', strict_slashes=True)
# def fsdf_home():
#     return render_template('fsdf_home.html')


@routes.route('/', strict_slashes=True)
def home():
    return render_template('home.html', home_page_settings=conf.home_page_boxes_dict)


@routes.route('/loc_info/')
def sa1s_loc_info():
    return get_register_items()

@routes.route('/loc_info/<string:loc_info_id>')
def sa1_loc_info_element(loc_info_id):
    sa1_aeip = SA1_LOC_INFO(request, request.base_url)
    return sa1_aeip.render()

@routes.route('/building_exposure/')
def sa1s_buld_expo():
    return get_register_items()

@routes.route('/building_exposure/<string:buld_expo_id>')
def sa1_buld_expo_element(buld_expo_id):
    sa1_aeip = SA1_BULD_EXPO(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/SEIFA/')
def sa1s_seifa():
    return get_register_items()

@routes.route('/SEIFA/<string:seifa_id>')
def sa1_seifa_element(seifa_id):
    sa1_aeip = SA1_SEIFA(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/demographic_exposure/')
def sa1s_demo():
    return get_register_items()

@routes.route('/demographic_exposure/<string:demo_id>')
def sa1_demo_element(demo_id):
    sa1_aeip = SA1_DEMO(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/economic_exposure/')
def sa1s_econ():
    return get_register_items()

@routes.route('/economic_exposure/<string:econ_id>')
def sa1_econ_element(econ_id):
    sa1_aeip = SA1_ECON(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/institution_exposure/')
def sa1s_inst():
    return get_register_items()

@routes.route('/institution_exposure/<string:inst_id>')
def sa1_inst_element(inst_id):
    sa1_aeip = SA1_INST(request, request.base_url)
    return sa1_aeip.render()

@routes.route('/transport_exposure/')
def sa1s_transport():
    return get_register_items()

@routes.route('/transport_exposure/<string:transport_id>')
def sa1_transport_element(transport_id):
    sa1_aeip = SA1_TRANSPORT(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/utility_exposure/')
def sa1s_utility():
    return get_register_items()

@routes.route('/utility_exposure/<string:utility_id>')
def sa1_utility_element(utility_id):
    sa1_aeip = SA1_UTILITY(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/business_exposure/')
def sa1s_business():
    return get_register_items()

@routes.route('/business_exposure/<string:business_id>')
def sa1_business_element(business_id):
    sa1_aeip = SA1_BUSINESS(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/agriculture_exposure/')
def sa1s_agriculture():
    return get_register_items()

@routes.route('/agriculture_exposure/<string:agri_id>')
def sa1_agriculture_element(agri_id):
    sa1_aeip = SA1_AGRI(request, request.base_url)
    return sa1_aeip.render()


@routes.route('/environment_exposure/')
def sa1s_environment():
    return get_register_items()

@routes.route('/environment_exposure/<string:envi_id>')
def sa1_environment_element(envi_id):
    sa1_aeip = SA1_ENVI(request, request.base_url)
    return sa1_aeip.render()



@routes.route('/map')
def show_map():
    '''
    Function to render a map around the specified line
    '''

    # import pdb
    # pdb.set_trace()

    name = request.values.get('name')
    coords_list = ast.literal_eval(request.values.get('coords'))
    geom_type = request.values.get('geom_type')

    if geom_type == "MultiPolygon":
        poly_points = []
        total_points = [] #used to calculate the average coordinates of the area of interest
        for a_polygon_coords in coords_list[0]: # may have more than one polygon
            points = []
            for coords in a_polygon_coords:
                points.append(tuple([coords[1], coords[0]]))   # swap x & y for mapping
                total_points.append(tuple([coords[1], coords[0]]))
            poly_points.append(points)
        ave_lat = sum(p[0] for p in total_points) / len(total_points)
        ave_lon = sum(p[1] for p in total_points) / len(total_points)

        lon_diff = max(p[1] for p in total_points) - min(p[1] for p in total_points)
        lat_diff = max(p[0] for p in total_points) - min(p[0] for p in total_points)
        ave_diff = (lon_diff + lat_diff)/2
        if ave_diff > 0.47:
            zoom_start_level = 8
        elif ave_diff > 0.3:
            zoom_start_level = 9
        elif ave_diff > 0.2:
            zoom_start_level = 10
        elif ave_diff > 0.1:
            zoom_start_level = 11
        elif ave_diff > 0.02:
            zoom_start_level = 12
        elif ave_diff > 0.01:
            zoom_start_level = 13
        elif ave_diff > 0.007:
            zoom_start_level = 14
        else:
            zoom_start_level = 15


        # create a new map object
        folium_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=zoom_start_level)
        tooltip = 'Click for more information'
        for a_poly_point in poly_points:
            folium.Polygon(a_poly_point, color="red", weight=2.5, opacity=1, popup=name, tooltip=tooltip).add_to(folium_map)
    elif geom_type == 'MultiLine': #polyline
        for a_line_coords in coords_list[0]:
            points = []
            for coords in a_line_coords:
                points.append(tuple([coords[1], coords[0]]))
            ave_lat = sum(p[0] for p in points) / len(points)
            ave_lon = sum(p[1] for p in points) / len(points)
            # create a new map object
            folium_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=13)
            tooltip = 'Click for more information'
            folium.PolyLine(points, color="red", weight=2.5, opacity=1, popup = name, tooltip=tooltip).add_to(folium_map)
    else: #point
        # create a new map object
        lat = coords_list[1]
        lon = coords_list[0]
        folium_map = folium.Map(location=[lat, lon], zoom_start=15)
        tooltip = 'Click for more information'
        folium.Marker([lat, lon], popup=name, tooltip=tooltip).add_to(folium_map)

    # if len(coords_list) == 1:  #polyline or polygon
    #     # swap x & y for mapping
    #     points = []
    #     if len(coords_list[0]) == 1: #polygon
    #         for coords in coords_list[0][0]:
    #             points.append(tuple([coords[1], coords[0]]))
    #         ave_lat = sum(p[0] for p in points) / len(points)
    #         ave_lon = sum(p[1] for p in points) / len(points)
    #         # create a new map object
    #         folium_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=12)
    #         tooltip = 'Click for more information'
    #         folium.Polygon(points, color="red", weight=2.5, opacity=1, popup=name, tooltip=tooltip).add_to(folium_map)
    #     else: #polyline
    #         for coords in coords_list[0]:
    #             points.append(tuple([coords[1], coords[0]]))
    #         ave_lat = sum(p[0] for p in points) / len(points)
    #         ave_lon = sum(p[1] for p in points) / len(points)
    #         # create a new map object
    #         folium_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=13)
    #         tooltip = 'Click for more information'
    #         folium.PolyLine(points, color="red", weight=2.5, opacity=1, popup = name, tooltip=tooltip).add_to(folium_map)
    # else: #point
    #     # create a new map object
    #     lat = coords_list[1]
    #     lon = coords_list[0]
    #     folium_map = folium.Map(location=[lat, lon], zoom_start=15)
    #     tooltip = 'Click for more information'
    #     folium.Marker([lat, lon], popup=name, tooltip=tooltip).add_to(folium_map)

    return folium_map.get_root().render()




def get_register_items():
    # Search specific items using keywords
    search_string = request.values.get('search')
    try:
        # get the register length from the online DB
        # sql = 'SELECT COUNT(*) FROM "AEIP_SA1join84"'
        sql = 'SELECT COUNT(*) FROM "{table}"'.format(table=TABLE_NAME)
        if search_string:
            sql += '''WHERE UPPER(cast("id" as text)) LIKE '%{search_string}%' OR UPPER("{name}") LIKE '%{search_string}%';
                   '''.format(name=NAME_FIELD, search_string=search_string.strip().upper())

        no_of_items = conf.db_select(sql)[0][0]

        page = int(request.values.get('page')) if request.values.get('page') is not None else 1
        per_page = int(request.values.get('per_page')) \
                   if request.values.get('per_page') is not None else DEFAULT_ITEMS_PER_PAGE
        offset = (page - 1) * per_page

        # get the id and name for each record in the database
        sql = '''SELECT "id", "{name}" FROM "{table}"'''.format(name=NAME_FIELD, table=TABLE_NAME)
        if search_string:
            sql += '''WHERE UPPER(cast("id" as text)) LIKE '%{search_string}%' OR UPPER("{name}") LIKE '%{search_string}%'
                   '''.format(name=NAME_FIELD, search_string=search_string.strip().upper())
        sql += '''ORDER BY "{name}"
                OFFSET {offset} LIMIT {per_page}'''.format(name=NAME_FIELD, offset=offset, per_page=per_page)

        items = []
        for item in conf.db_select(sql):
            items.append(
                (item[0], item[1])
            )
    except Exception as e:
        print(e)
        return Response('The database is offline', mimetype='text/plain', status=500)

    return ContainerRenderer(request=request,
                            instance_uri=request.url,
                            label='SA1 with AEIP Register',
                            comment='A register of SA1s with info from AEIP (Australian Exposure Information Platform)',
                            parent_container_uri='http://linked.data.gov.au/def/placenames/PlaceName',
                            parent_container_label='SA1',
                            members=items,
                            members_total_count=no_of_items,
                            profiles=None,
                            default_profile_token=None,
                            super_register=None,
                            page_size_max=1000,
                            register_template=None,
                            per_page=per_page,
                            search_query=search_string,
                            search_enabled=True
                            ).render()