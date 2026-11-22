extends Node2D
# S3: a sprite that sways for 1 s; the background must stay transparent in captured frames.
var t := 0.0
@onready var s: Sprite2D = $Sprite
func _process(delta: float) -> void:
	t += delta
	s.rotation = sin(t * TAU) * 0.15
