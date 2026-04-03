const express = require("express")
const mongoose = require("mongoose")
const cors = require("cors")
const bodyParser = require("body-parser")
const cookieParser = require("cookie-parser")

const app = express()

app.use(cors({
    origin: "http://127.0.0.1:5500", // your frontend
    credentials: true
}))
app.use(bodyParser.json())
app.use(cookieParser())

// CONNECT DB
mongoose.connect("mongodb://127.0.0.1:27017/ai_pest_users")

// USER MODEL
const User = mongoose.model("User", {
    fullname: String,
    email: String,
    password: String
})

/* ================= SIGNUP ================= */
app.post("/signup", async (req, res) => {
    const { fullname, email, password } = req.body

    const existing = await User.findOne({ email })
    if (existing) {
        return res.json({ status: "fail", message: "User already exists" })
    }

    const user = new User({ fullname, email, password })
    await user.save()

    res.json({ status: "success" })
})

/* ================= LOGIN ================= */
app.post("/login", async (req, res) => {
    const { email, password } = req.body

    const user = await User.findOne({ email, password })

    if (!user) {
        return res.json({ status: "fail" })
    }

    res.cookie("user", user.email, { httpOnly: true })
    res.json({ status: "success" })
})

/* ================= CHECK LOGIN ================= */
app.get("/check-login", (req, res) => {
    if (req.cookies.user) {
        res.json({ logged_in: true, email: req.cookies.user })
    } else {
        res.json({ logged_in: false })
    }
})

/* ================= LOGOUT ================= */
app.get("/logout", (req, res) => {
    res.clearCookie("user")
    res.json({ status: "logged out" })
})

app.listen(9000, () => console.log("Server running on 9000"))