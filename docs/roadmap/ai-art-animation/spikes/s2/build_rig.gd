extends SceneTree
# Spike S2: build a Godot 4.6 Skeleton2D + weighted Polygon2D rig and an AnimationPlayer clip from
# engine-neutral JSON (rig.json, clip_sway.json), then save res://s2_rig.tscn. Run headless:
#   godot --headless --path . --script res://build_rig.gd

func _init() -> void:
	var rig: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://rig.json"))
	var clip: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://clip_sway.json"))
	var root := Node2D.new()
	root.name = "ScrivenerRig"
	var skel := Skeleton2D.new()
	skel.name = "Skeleton2D"
	root.add_child(skel)
	skel.owner = root

	# Bones: Bone2D positions are relative to the parent bone; pivots are in image pixels.
	var nodes := {}
	var paths := {}
	var pivots := {}
	for b in rig["bones"]:
		var bone := Bone2D.new()
		bone.name = b["name"]
		var pv := Vector2(b["pivot"][0], b["pivot"][1])
		pivots[b["name"]] = pv
		var parent_node: Node = skel if b["parent"] == null else nodes[b["parent"]]
		var parent_pv: Vector2 = Vector2.ZERO if b["parent"] == null else pivots[b["parent"]]
		bone.position = pv - parent_pv
		bone.set_autocalculate_length_and_angle(false)
		bone.set_length(float(b["length"]))
		bone.set_bone_angle(-PI / 2.0)
		parent_node.add_child(bone)
		bone.owner = root
		bone.rest = bone.transform
		nodes[b["name"]] = bone
		paths[b["name"]] = NodePath(("" if b["parent"] == null else String(paths[b["parent"]]) + "/") + b["name"])

	# Parts in draw order: Polygon2D with UVs = image pixels, triangles, and per-bone weights.
	var by_name := {}
	for p in rig["parts"]:
		by_name[p["name"]] = p
	for pname in rig["draw_order"]:
		var p: Dictionary = by_name[pname]
		var poly := Polygon2D.new()
		poly.name = pname
		poly.texture = load("res://" + p["texture"])
		var pts := PackedVector2Array()
		for v in p["vertices"]:
			pts.append(Vector2(v[0], v[1]))
		poly.polygon = pts
		poly.uv = pts
		var tris := []
		for t in p["triangles"]:
			tris.append(PackedInt32Array(t))
		poly.polygons = tris
		root.add_child(poly)
		poly.owner = root
		poly.skeleton = poly.get_path_to(skel)
		for bone_name in p["weights"].keys():
			poly.add_bone(paths[bone_name], PackedFloat32Array(p["weights"][bone_name]))

	# Clip -> Animation (rotation tracks on bones, relative to the rest angle).
	var anim := Animation.new()
	anim.length = float(clip["length"])
	anim.loop_mode = Animation.LOOP_LINEAR if clip["loop"] else Animation.LOOP_NONE
	for bone_name in clip["tracks"].keys():
		var tr := anim.add_track(Animation.TYPE_VALUE)
		anim.track_set_path(tr, NodePath("Skeleton2D/" + String(paths[bone_name]) + ":rotation"))
		anim.track_set_interpolation_type(tr, Animation.INTERPOLATION_CUBIC)
		for k in clip["tracks"][bone_name]:
			anim.track_insert_key(tr, float(k[0]), float(k[1]))
	var lib := AnimationLibrary.new()
	lib.add_animation(clip["name"], anim)
	var ap := AnimationPlayer.new()
	ap.name = "AnimationPlayer"
	root.add_child(ap)
	ap.owner = root
	ap.add_animation_library("", lib)
	ap.autoplay = clip["name"]

	var ps := PackedScene.new()
	var err := ps.pack(root)
	if err == OK:
		err = ResourceSaver.save(ps, "res://s2_rig.tscn")
	print("S2 build: ", "OK" if err == OK else "error %d" % err, " bones=", nodes.size(), " parts=", rig["parts"].size())
	quit(0 if err == OK else 1)
