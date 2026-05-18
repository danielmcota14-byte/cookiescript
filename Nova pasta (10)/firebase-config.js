// Firebase Configuration
export const firebaseConfig = {
    apiKey: "AIzaSyAc4-Mg31Vo-uL1UjeyxM0prrTcdd9YlX0",
    authDomain: "nibtrader-52b9a.firebaseapp.com",
    databaseURL: "https://nibtrader-52b9a-default-rtdb.firebaseio.com",
    projectId: "nibtrader-52b9a",
    storageBucket: "nibtrader-52b9a.firebasestorage.app",
    messagingSenderId: "859734884174",
    appId: "1:859734884174:web:60d74496bd279bea28e81f"
};

// Inicializar Firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword,
    updateProfile,
    signOut,
    onAuthStateChanged 
} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";
import { 
    getDatabase, 
    ref, 
    set, 
    get, 
    push, 
    update, 
    remove, 
    query, 
    orderByChild, 
    equalTo 
} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-database.js";

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const database = getDatabase(app);

// Exportar funções do Firebase
export { 
    ref, set, get, push, update, remove, query, orderByChild, equalTo,
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword,
    updateProfile,
    signOut,
    onAuthStateChanged
};