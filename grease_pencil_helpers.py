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

# from https://github.com/sakana3/PolyQuilt/tree/master/Addons/PolyQuilt / LICENSE GNU
def get_gp_layer(context, layer_name = "Annotations") :
        gp = context.scene.grease_pencil
        if not gp:
            gp = bpy.data.grease_pencils.new("GP")
            context.scene.grease_pencil = gp

        layer = None
        if not layer_name :
            if gp.layers.active :
                layer = gp.layers.active
            elif len(gp.layers) > 0 :
                layer = gp.layers[0]
                gp.layers.active = layer
        else :
            if any( layer_name in l.info for l in  gp.layers ) :
                for l in gp.layers :
                    if layer_name in l.info : 
                        layer = l
                        break
            else :
                layer = gp.layers.new(layer_name , set_active = gp.layers.active == None )
                gp.layers.active = layer

        return layer

# from https://github.com/sakana3/PolyQuilt/tree/master/Addons/PolyQuilt / LICENSE GNU
def get_gp_frame(layer) :
    if len(layer.frames) == 0 :
        layer.frames.new(1, active = True)
    frame = layer.active_frame 
    return frame

# UVエディタのエリアを探す
def get_gp_layer_for_uv_editor() :
    for area in bpy.context.screen.areas:
        print(area.type)
        if area.type == 'IMAGE_EDITOR':
            for s in area.spaces :            
                for layer in s.grease_pencil.layers :
                    return layer