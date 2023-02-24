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
    "name": "ConfirmWire",
    "description": "check the edges",
    "author": "Yuuzen401",
    "version": (0, 0, 4),
    "blender": (2, 80, 0),
    "location":  "View3D > Sidebar > Confirm Wire",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://github.com/Yuuzen401/ConfirmWire",
    "category": "Object"
}

import bpy
import gpu
import bgl
import bmesh
import math

from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, PointerProperty
from gpu_extras.batch import batch_for_shader
from .helper import *
from .mesh_helpers import *

# Updater ops import, all setup in this file.
from . import addon_updater_ops

def update_cw_target(self, context):
    ConfirmWireOperator.force_disable()

class ConfirmWirePropertyGroup(bpy.types.PropertyGroup):

    # 対象オブジェクト
    cw_target : PointerProperty(name = "target", type = bpy.types.Object, poll = lambda self, obj: obj.type == 'MESH', update = update_cw_target)
    # 線の太さ
    cw_line_width : IntProperty(name = "width", default = 1, min = 1, max = 10)
    # 線の透明度
    cw_line_alpha : FloatProperty(name = "alpha", default = 0.5, min = 0, max = 1, precision = 1)
    # 線の色
    cw_line_color : FloatVectorProperty(name = 'color', subtype = 'COLOR', min = 0.0, max = 1, default = (0.0, 1.0, 0.0) ,precision = 1)
    # 左右反転するか
    cw_is_flip_horizontal : BoolProperty(name = "flip horizontal", default = False)
    # モディファイアの評価を有効にするか
    cw_is_modifier : BoolProperty(name = "modifier", default = False)
    # 隠れた線も表示するか
    cw_is_xray : BoolProperty(name = "xray", default = False)
    # 処理可能な頂点数
    cw_max_vertex : IntProperty(name = "max vertex", default = 100000, min = 10000, max = 200000)

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
        prop = context.scene.confirm_wire_prop
        obj = prop.cw_target
        bm = bmesh_copy_from_object(obj, True, False, prop.cw_is_modifier)

        # 頂点数が多すぎると負荷が高いため処理を中止する
        vertex_count = len(bm.verts)
        if vertex_count > prop.cw_max_vertex:
            bm.free()
            self.force_disable()
            show_message_error('canceled because there are too many vertices.')
            return

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

        coords = []
        for v in bm.verts:
            co = v.co.copy()
            coords.append(co)

        if prop.cw_is_flip_horizontal:
            coords = [(v[0]*-1, v[1], v[2]) for v in coords]

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(prop.cw_line_width)

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        rgb = prop.cw_line_color
        shader.uniform_float("color", (rgb[0], rgb[1], rgb[2], prop.cw_line_alpha))
        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices = indices)
        batch.draw(shader)

        # 透過か
        if prop.cw_is_xray:
            batch_xray = batch_for_shader(shader, 'LINES', {"pos": coords}, indices = indices_xray)
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
        prop = context.scene.confirm_wire_prop
        layout = self.layout
        obj = prop.cw_target

        # -------------------------------------------------
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_target")
        layout.separator()

        if prop.cw_target is None:
            return

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
        row.prop(prop, "cw_line_color")

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
        row.scale_y = 2
        if ConfirmWireOperator.is_enable():
            row.operator(ConfirmWireOperator.bl_idname, text = "Confirm Wire Enable", depress = True,  icon = "PAUSE") 
        else:
            row.operator(ConfirmWireOperator.bl_idname, text = "Confirm Wire Enable", depress = False, icon = "PLAY")

        layout.separator()
        row = layout.row()
        row.prop(prop, "cw_max_vertex", icon = "OUTLINER_DATA_MESH")

class ConfirmWireUpdaterPanel(bpy.types.Panel):
    bl_label = "Updater ConfirmWire Panel"
    bl_idname = "OBJECT_PT_ConfirmWireUpdaterPanel_hello"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS' if bpy.app.version < (2, 80) else 'UI'
    bl_context = "objectmode"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout

        # Call to check for update in background.
        # Note: built-in checks ensure it runs at most once, and will run in
        # the background thread, not blocking or hanging blender.
        # Internally also checks to see if auto-check enabled and if the time
        # interval has passed.
        addon_updater_ops.check_for_update_background()

        layout.label(text="ConfirmWire Updater Addon")
        layout.label(text="")

        col = layout.column()
        col.scale_y = 0.7
        col.label(text="If an update is ready,")
        col.label(text="popup triggered by opening")
        col.label(text="this panel, plus a box ui")

        # Could also use your own custom drawing based on shared variables.
        if addon_updater_ops.updater.update_ready:
            layout.label(text="Custom update message", icon="INFO")
        layout.label(text="")

        # Call built-in function with draw code/checks.
        addon_updater_ops.update_notice_box_ui(self, context)

@addon_updater_ops.make_annotations
class ConfirmWirePreferences(bpy.types.AddonPreferences):
    """ConfirmWire bare-bones preferences"""
    bl_idname = __package__

    # Addon updater preferences.

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)

    def draw(self, context):
        layout = self.layout

        # Works best if a column, or even just self.layout.
        mainrow = layout.row()
        col = mainrow.column()

        # Updater draw function, could also pass in col as third arg.
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # ops = col.operator("wm.url_open","Open webpage ")
        # ops.url=addon_updater_ops.updater.website

classes = (
    ConfirmWirePropertyGroup,
    ConfirmWireOperator,
    ConfirmWirePanel,
    ConfirmWirePreferences,
    ConfirmWireUpdaterPanel
    )

def register():
    addon_updater_ops.register(bl_info)
    for cls in classes:
        addon_updater_ops.make_annotations(cls)  # Avoid blender 2.8 warnings.
        bpy.utils.register_class(cls)
    bpy.types.Scene.confirm_wire_prop = bpy.props.PointerProperty(type = ConfirmWirePropertyGroup)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.confirm_wire_prop

    addon_updater_ops.unregister()

if __name__ == "__main__":
    register()