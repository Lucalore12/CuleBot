# bot_discord/models.py

from django.db import models

class Mensaje(models.Model):
    canal_id = models.CharField(max_length=100)
    usuario_id = models.CharField(max_length=100)
    nombre_usuario = models.CharField(max_length=100)
    nombre_global = models.CharField(max_length=100, null=True, blank=True)
    contenido_mensaje = models.TextField()
    respuesta_modelo = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nombre_usuario} ({self.usuario_id}): {self.contenido_mensaje[:50]}...'


class CanalHabilitado(models.Model):
    canal_id = models.CharField(max_length=50, unique=True)
    fecha_habilitado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Canal ID: {self.canal_id}'
