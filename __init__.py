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

bl_info = {
    "name": "Confirm Wire",
    "description": "check the edges",
    "author": "Yuuzen401",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location":  "View3D > Sidebar > Confirm Wire",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

import bpy
import gpu
import bgl
import bmesh
import math
from gpu_extras.batch import batch_for_shader
from .helper import *

class ConfirmWirePropertyGroup(bpy.types.PropertyGroup):
    # 対象オブジェクト
    cw_target : bpy.props.PointerProperty(name = "target", type = bpy.types.Object, poll = lambda self, obj: obj.type == 'MESH')
    # 線の太さ
    cw_line_width : bpy.props.IntProperty(name = "width", default = 1, min = 1, max = 10)
    # 線の透明度
    cw_line_alpha : bpy.props.FloatProperty(name = "alpha", default = 0.5, min = 0, max = 1, precision = 1)
    # 線の色
    cw_line_color : bpy.props.FloatVectorProperty(name = 'color', subtype = 'COLOR', min = 0.0, max = 1, default = (0.0, 1.0, 0.0) ,precision = 1)
    # 左右反転するか
    cw_is_flip_horizontal : bpy.props.BoolProperty(name = "flip horizontal", default = False)
    # モディファイアの評価を有効にするか
    cw_is_modifier : bpy.props.BoolProperty(name = "modifier", default = False)
    # 隠れた線も表示するか
    cw_is_xray : bpy.props.BoolProperty(name = "xray", default = False)

class ConfirmWireOperator(bpy.types.Operator):
    bl_idname = "confirm_wire.operator"
    bl_label = "Confirm Wire"

    # 描画ハンドラ
    draw_handler = None

    @classmethod
    def is_enable(self):
        # 描画ハンドラがNone以外のときは描画中であるため、Trueを返す
        return True if self.draw_handler else False

    @classmethod
    def force_disable(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
        self.draw_handler = None
        area_3d_view_tag_redraw_all()

    @classmethod
    def __handle_add(self, context):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.__draw, (context, ), 'WINDOW', 'POST_VIEW')

    @classmethod
    def __handle_remove(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
        self.draw_handler = None

    @classmethod
    def __draw(self, context):
        prop = context.scene.my_prop
        obj = prop.cw_target

        if is_mesh_edit(obj):
            bm = bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new()
            # モディファイアによる評価済のオブジェクトで描画するか
            if (prop.cw_is_modifier):
                depsgraph = context.evaluated_depsgraph_get()
                bm.from_object(obj, depsgraph)
            else:
                bm.from_mesh(obj.data)

        indices = []
        indices_xray = []
        for e in bm.edges:
            v1 = e.verts[0]
            v2 = e.verts[1]
            normal = v1.normal + v2.normal

            # 左右反転か
            if prop.cw_is_flip_horizontal:
                normal.x = normal.x * -1

            # 3DVIEWから見て、法線の向きが内側であるか
            if is_in_normal_from_view_3d(context, normal):
                if prop.cw_is_xray:
                    indices_xray.append((e.verts[0].index, e.verts[1].index))
                continue

            indices.append((e.verts[0].index, e.verts[1].index))

        coords = [v.co + obj.location for v in bm.verts]
        if prop.cw_is_flip_horizontal:
            coords = [(v[0]*-1, v[1], v[2]) for v in coords]

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(prop.cw_line_width)

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        rgb = prop.cw_line_color
        shader.uniform_float("color", (rgb[0], rgb[1], rgb[2], prop.cw_line_alpha))
        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        batch.draw(shader)

        # 透過か
        if prop.cw_is_xray:
            batch_xray = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices_xray)
            shader.uniform_float("color", (rgb[0], rgb[1], rgb[2], prop.cw_line_alpha * 0.5))
            batch_xray.draw(shader)

        bgl.glDisable(bgl.GL_BLEND)

        # 対象が編集時以外はbmeshを解放する
        if is_mesh_edit(obj) == False:
            bm.free()

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            # enable to disable
            if self.is_enable():
                self.__handle_remove(context)
            # disable to enable
            else:
                self.__handle_add(context)

            # 全エリアを再描画（アクティブな画面以外も再描画する）
            area_3d_view_tag_redraw_all()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class ConfirmWirePanel(bpy.types.Panel):
    bl_label = "Confirm Wire"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Confirm Wire"

    def draw(self, context):
        prop = context.scene.my_prop
        layout = self.layout
        obj = prop.cw_target

        # -------------------------------------------------
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_target")
        layout.separator()

        if prop.cw_target is None:
            ConfirmWireOperator.force_disable()
            layout.enable = False

        # -------------------------------------------------
        box = layout.box()

        row = box.row()
        row.label(text = 'line style')

        row = box.row()
        row.separator()
        row.prop(prop, "cw_line_width")

        row = box.row()
        row.separator()
        row.prop(prop, "cw_line_alpha")

        row = box.row()
        row.separator()
        row.prop(context.scene.my_prop, "cw_line_color")

        # -------------------------------------------------
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_is_flip_horizontal", icon = "ARROW_LEFTRIGHT")
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_is_modifier", icon = "MODIFIER")
        
        # 編集モードで評価済みのオブジェクトで描画できないため明示的に無効する
        if is_mesh_edit(obj):
            row.enabled = False

        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_is_xray", icon = "XRAY")

        # -------------------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row()
        row.scale_y = 1.5
        if ConfirmWireOperator.is_enable():
            row.operator(ConfirmWireOperator.bl_idname, text = "enable", depress = True) 
        else:
            row.operator(ConfirmWireOperator.bl_idname, text = "enable", depress = False)

classes = (
    ConfirmWirePropertyGroup,
    ConfirmWireOperator,
    ConfirmWirePanel,
    )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.my_prop = bpy.props.PointerProperty(type=ConfirmWirePropertyGroup)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.my_prop

if __name__ == "__main__":
    register()