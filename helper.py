# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
import math

# def get_region_view_3d(context):
#     area = get_area_view_3d(context)
#     if area is None:
#         return None

#     for region in area.regions:
#         if region.type == 'WINDOW':
#             return region
#     else:
#         return None

# アクティブなエリアのSpaceView3Dを取得する
def get_space_view_3d(context):
    aria = bpy.context.area
    if aria is None:
        return None

    for space in aria.spaces:
        if space.type == 'VIEW_3D':
            return space
    else:
        return None

# def get_space_view_3d_euler_z(context):
#     space_view_3d = get_space_view_3d(context)
#     if space_view_3d:
#         view_rotation = space_view_3d.region_3d.view_rotation
#         return math.degrees(view_rotation.to_euler().z)
#     else:
#         return None

# def get_space_view_3d_vector(context):
#     space_view_3d = get_space_view_3d(context)
#     if space_view_3d:
#         return space_view_3d.region_3d.view_location
#     else:
#         return None

# 用途：法線からZ軸のオイラー角度を取得する
# def vector_to_euler_z(vector):
#     vector.normalize()
#     euler = vector.to_track_quat('Z', 'Y').to_euler()
#     return math.degrees(euler.z)

# VIEW3Dの視点から、法線が内側であるか
def is_in_normal_from_view_3d(context, normal):
    space_view_3d = get_space_view_3d(context)
    matrix_z = space_view_3d.region_3d.view_rotation.to_matrix().col[2]
    return normal.dot(matrix_z) < 0

# カラーコードから10進数に変換
# def hex_code_to_rgb_int_0_255(hex_code):
#     r = int(hex_code[1:3], 16)
#     g = int(hex_code[3:5], 16)
#     b = int(hex_code[5:7], 16)
#     return (r, g, b)

# カラーコードからrgbの値を0.0～1.0の範囲に変換する
# def hex_code_to_rgb_dec_0_1(hex_code):
#     rgb = hex_code_to_rgb_int_0_255(hex_code)
#     return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)

def is_mesh_edit(obj):
    return obj and obj.mode == 'EDIT' and obj.type == 'MESH'

def area_3d_view_tag_redraw_all():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def show_message_info(message):
    def draw(self, context):
        self.layout.label(text = message)
    bpy.context.window_manager.popup_menu(draw, title = "Message", icon = "INFO")

def show_message_error(message):
    def draw(self, context):
        self.layout.label(text = message)
    bpy.context.window_manager.popup_menu(draw, title = 'Error', icon = 'ERROR')