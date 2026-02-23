<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" class="pa-4">
          <v-card-title class="text-center text-h4 font-weight-bold py-6">
            <v-icon size="40" color="primary" class="mr-2">mdi-camera-iris</v-icon>
            Photobooth
          </v-card-title>

          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="mail"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email-outline"
                variant="outlined"
                class="mb-3"
                autofocus
                :disabled="loading"
              />
              <v-text-field
                v-model="password"
                label="Mot de passe"
                type="password"
                prepend-inner-icon="mdi-lock-outline"
                variant="outlined"
                class="mb-4"
                :disabled="loading"
              />
              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
              >
                Se connecter
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="error" color="error" :timeout="3000" location="top">
      {{ errorMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const mail = ref('')
const password = ref('')
const loading = ref(false)
const error = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  if (!mail.value || !password.value) return
  loading.value = true
  try {
    await auth.login(mail.value, password.value)
  } catch (e) {
    errorMessage.value = e.response?.data?.error ?? 'Erreur de connexion'
    error.value = true
  } finally {
    loading.value = false
  }
}
</script>
