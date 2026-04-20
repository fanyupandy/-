from datetime import datetime

from flask import Flask, jsonify, render_template_string, request
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///club_manager.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(120), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    memberships = db.relationship(
        "Membership",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_id": self.student_id,
            "department": self.department,
            "join_date": self.join_date.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    avatar = db.Column(db.Text, default="", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    memberships = db.relationship(
        "Membership",
        back_populates="club",
        cascade="all, delete-orphan",
        order_by="Membership.created_at.desc()",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "avatar": self.avatar,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "member_count": len(self.memberships),
        }


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, default="队员")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("club.id"), nullable=False)

    student = db.relationship("Student", back_populates="memberships")
    club = db.relationship("Club", back_populates="memberships")

    __table_args__ = (
        db.UniqueConstraint("student_id", "club_id", name="uq_membership_student_club"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "student": self.student.to_dict(),
            "club_id": self.club_id,
        }


VALID_ROLES = {"队员", "副社长", "社长"}

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>社团管理系统</title>
    <style>
        :root {
            --bg: #0b1220;
            --panel: #111a2e;
            --panel-2: #16233d;
            --border: rgba(255, 255, 255, 0.08);
            --text: #e7edf7;
            --muted: #9fb0cc;
            --primary: #5eead4;
            --accent: #f59e0b;
            --danger: #fb7185;
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(94, 234, 212, 0.14), transparent 25%),
                radial-gradient(circle at bottom right, rgba(245, 158, 11, 0.12), transparent 25%),
                linear-gradient(135deg, #08111f 0%, #0f172a 45%, #101827 100%);
            color: var(--text);
            min-height: 100vh;
        }

        .wrap {
            max-width: 1280px;
            margin: 0 auto;
            padding: 24px;
        }

        .hero {
            margin-bottom: 24px;
            padding: 24px;
            border: 1px solid var(--border);
            border-radius: 24px;
            background: rgba(17, 26, 46, 0.78);
            backdrop-filter: blur(14px);
        }

        .hero h1 {
            margin: 0 0 8px;
            font-size: 32px;
        }

        .hero p {
            margin: 0;
            color: var(--muted);
        }

        .toolbar {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 18px;
        }

        .layout {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 24px;
        }

        .panel {
            border: 1px solid var(--border);
            border-radius: 24px;
            background: rgba(17, 26, 46, 0.8);
            padding: 20px;
            backdrop-filter: blur(14px);
        }

        .panel h2, .panel h3 {
            margin-top: 0;
        }

        .club-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .club-card {
            width: 100%;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.03);
            color: inherit;
            text-align: left;
            padding: 14px;
            cursor: pointer;
        }

        .club-card.active {
            border-color: rgba(94, 234, 212, 0.45);
            background: rgba(94, 234, 212, 0.08);
        }

        .club-card small {
            color: var(--muted);
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1.1fr 1fr;
            gap: 20px;
        }

        .form-row {
            margin-bottom: 14px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: var(--muted);
        }

        input, textarea, select {
            width: 100%;
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.04);
            color: var(--text);
        }

        select {
            color: #111;
            background: #fff;
        }

        select option {
            color: #111;
            background: #fff;
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        button {
            border: 0;
            border-radius: 14px;
            padding: 11px 16px;
            cursor: pointer;
            font-weight: 700;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent), var(--primary));
            color: #04111d;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text);
            border: 1px solid var(--border);
        }

        .btn-danger {
            background: rgba(251, 113, 133, 0.12);
            color: #fecdd3;
            border: 1px solid rgba(251, 113, 133, 0.32);
        }

        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .profile-head {
            display: flex;
            gap: 16px;
            align-items: center;
            margin-bottom: 16px;
        }

        .avatar {
            width: 84px;
            height: 84px;
            border-radius: 22px;
            overflow: hidden;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.06);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            color: var(--muted);
        }

        .avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            text-align: left;
            vertical-align: middle;
        }

        th {
            color: var(--muted);
            font-size: 14px;
        }

        .muted {
            color: var(--muted);
        }

        .message {
            margin-bottom: 16px;
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.05);
        }

        .message.error {
            border-color: rgba(251, 113, 133, 0.35);
            color: #fecdd3;
        }

        .empty {
            padding: 28px;
            border: 1px dashed var(--border);
            border-radius: 18px;
            color: var(--muted);
            text-align: center;
        }

        @media (max-width: 980px) {
            .layout, .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <section class="hero">
            <h1>社团管理系统</h1>
            <p>支持创建社团、编辑简介与头像、添加成员、调整职位，并删除不再需要的社团。</p>
            <div class="toolbar">
                <button class="btn-primary" id="createClubBtn">新建社团</button>
                <button class="btn-secondary" id="refreshBtn">刷新数据</button>
            </div>
        </section>

        <div id="message" class="message" style="display:none;"></div>

        <div class="layout">
            <aside class="panel">
                <h2>社团列表</h2>
                <div id="clubStats" class="muted" style="margin-bottom: 14px;">加载中...</div>
                <div id="clubList" class="club-list"></div>
            </aside>

            <main class="panel">
                <div id="emptyState" class="empty" style="display:none;">
                    还没有社团。点击“新建社团”开始创建。
                </div>

                <div id="dashboard" style="display:none;">
                    <div class="grid-2">
                        <section>
                            <div class="profile-head">
                                <div class="avatar" id="avatarBox">社团</div>
                                <div>
                                    <h2 id="clubTitle" style="margin:0 0 6px;"></h2>
                                    <div id="clubMeta" class="muted"></div>
                                </div>
                            </div>

                            <form id="clubProfileForm">
                                <div class="form-row">
                                    <label for="clubNameInput">社团名称</label>
                                    <input id="clubNameInput" name="name" required>
                                </div>
                                <div class="form-row">
                                    <label for="clubDescriptionInput">社团简介</label>
                                    <textarea id="clubDescriptionInput" name="description"></textarea>
                                </div>
                                <div class="form-row">
                                    <label for="clubAvatarInput">社团头像</label>
                                    <input id="clubAvatarInput" type="file" accept="image/*">
                                </div>
                                <div class="actions">
                                    <button type="submit" class="btn-primary">保存社团资料</button>
                                    <button type="button" id="deleteClubBtn" class="btn-danger">删除当前社团</button>
                                </div>
                            </form>
                        </section>

                        <section>
                            <h3>添加成员</h3>
                            <form id="memberForm">
                                <div class="form-row">
                                    <label for="memberNameInput">姓名</label>
                                    <input id="memberNameInput" name="name" required>
                                </div>
                                <div class="form-row">
                                    <label for="memberStudentIdInput">学号</label>
                                    <input id="memberStudentIdInput" name="student_id" required>
                                </div>
                                <div class="form-row">
                                    <label for="memberDepartmentInput">院系</label>
                                    <input id="memberDepartmentInput" name="department" required>
                                </div>
                                <div class="form-row">
                                    <label for="memberRoleInput">职位</label>
                                    <select id="memberRoleInput" name="role">
                                        <option value="队员">队员</option>
                                        <option value="副社长">副社长</option>
                                        <option value="社长">社长</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn-primary">添加到社团</button>
                            </form>
                        </section>
                    </div>

                    <section style="margin-top: 24px;">
                        <h3>社团成员</h3>
                        <div class="muted" style="margin-bottom: 12px;">可以直接修改职位，或将成员移出社团。</div>
                        <div style="overflow-x:auto;">
                            <table>
                                <thead>
                                    <tr>
                                        <th>姓名</th>
                                        <th>学号</th>
                                        <th>院系</th>
                                        <th>职位</th>
                                        <th>操作</th>
                                    </tr>
                                </thead>
                                <tbody id="memberTableBody"></tbody>
                            </table>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    </div>

    <script>
        const roleOptions = ["队员", "副社长", "社长"];
        const state = {
            clubs: [],
            selectedClubId: null,
            selectedClub: null,
            memberships: [],
            pendingClubAvatar: "",
            pendingNewClubAvatar: ""
        };

        function showMessage(message, type = "") {
            const el = document.getElementById("message");
            el.textContent = message;
            el.className = `message ${type}`.trim();
            el.style.display = "block";
        }

        function hideMessage() {
            document.getElementById("message").style.display = "none";
        }

        async function requestJson(url, options = {}) {
            const response = await fetch(url, options);
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "请求失败");
            }
            return data;
        }

        async function readFileAsDataUrl(file) {
            if (!file) return "";
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(new Error("读取图片失败"));
                reader.readAsDataURL(file);
            });
        }

        function renderClubList() {
            const list = document.getElementById("clubList");
            const stats = document.getElementById("clubStats");
            stats.textContent = `共 ${state.clubs.length} 个社团`;

            if (!state.clubs.length) {
                list.innerHTML = '<div class="empty">暂无社团</div>';
                return;
            }

            list.innerHTML = state.clubs.map(club => `
                <button class="club-card ${club.id === state.selectedClubId ? "active" : ""}" onclick="selectClub(${club.id})">
                    <div style="font-size:18px;font-weight:800;margin-bottom:6px;">${club.name}</div>
                    <small>${club.member_count} 人 · 创建于 ${club.created_at}</small>
                </button>
            `).join("");
        }

        function renderSelectedClub() {
            const emptyState = document.getElementById("emptyState");
            const dashboard = document.getElementById("dashboard");

            if (!state.selectedClub) {
                emptyState.style.display = "block";
                dashboard.style.display = "none";
                return;
            }

            emptyState.style.display = "none";
            dashboard.style.display = "block";

            document.getElementById("clubTitle").textContent = state.selectedClub.name;
            document.getElementById("clubMeta").textContent = `${state.selectedClub.member_count} 名成员`;
            document.getElementById("clubNameInput").value = state.selectedClub.name || "";
            document.getElementById("clubDescriptionInput").value = state.selectedClub.description || "";
            document.getElementById("clubAvatarInput").value = "";

            const avatarBox = document.getElementById("avatarBox");
            if (state.selectedClub.avatar) {
                avatarBox.innerHTML = `<img src="${state.selectedClub.avatar}" alt="社团头像">`;
            } else {
                avatarBox.textContent = state.selectedClub.name.slice(0, 2) || "社团";
            }
        }

        function renderMembers() {
            const tbody = document.getElementById("memberTableBody");
            if (!state.selectedClub) {
                tbody.innerHTML = "";
                return;
            }

            if (!state.memberships.length) {
                tbody.innerHTML = '<tr><td colspan="5" class="muted">当前社团还没有成员。</td></tr>';
                return;
            }

            tbody.innerHTML = state.memberships.map(item => `
                <tr>
                    <td>${item.student.name}</td>
                    <td>${item.student.student_id}</td>
                    <td>${item.student.department}</td>
                    <td>
                        <select onchange="updateMembershipRole(${item.id}, this.value)">
                            ${roleOptions.map(role => `<option value="${role}" ${item.role === role ? "selected" : ""}>${role}</option>`).join("")}
                        </select>
                    </td>
                    <td>
                        <button class="btn-danger" onclick="removeMembership(${item.id})">移出社团</button>
                    </td>
                </tr>
            `).join("");
        }

        async function loadClubs(preferredClubId = null) {
            const clubs = await requestJson("/api/clubs");
            state.clubs = clubs;

            if (!clubs.length) {
                state.selectedClubId = null;
                state.selectedClub = null;
                state.memberships = [];
                renderClubList();
                renderSelectedClub();
                renderMembers();
                return;
            }

            if (preferredClubId && clubs.some(club => club.id === preferredClubId)) {
                state.selectedClubId = preferredClubId;
            } else if (!state.selectedClubId || !clubs.some(club => club.id === state.selectedClubId)) {
                state.selectedClubId = clubs[0].id;
            }

            state.selectedClub = clubs.find(club => club.id === state.selectedClubId) || null;
            renderClubList();
            renderSelectedClub();
            await loadMembers(state.selectedClubId);
        }

        async function loadMembers(clubId) {
            if (!clubId) {
                state.memberships = [];
                renderMembers();
                return;
            }

            const data = await requestJson(`/api/clubs/${clubId}/members`);
            state.memberships = data.memberships || [];
            renderMembers();
        }

        async function refreshDashboard(preferredClubId = null) {
            hideMessage();
            try {
                await loadClubs(preferredClubId);
            } catch (error) {
                showMessage(error.message, "error");
            }
        }

        async function selectClub(clubId) {
            state.selectedClubId = clubId;
            state.selectedClub = state.clubs.find(club => club.id === clubId) || null;
            renderClubList();
            renderSelectedClub();
            await loadMembers(clubId);
        }

        async function updateMembershipRole(membershipId, role) {
            try {
                const data = await requestJson(`/api/memberships/${membershipId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ role })
                });
                showMessage(data.message || "成员职位更新成功。");
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message, "error");
            }
        }

        async function removeMembership(membershipId) {
            if (!window.confirm("确定要将该成员移出当前社团吗？")) return;

            try {
                const data = await requestJson(`/api/memberships/${membershipId}`, { method: "DELETE" });
                showMessage(data.message || "成员已移出社团。");
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message, "error");
            }
        }

        async function deleteSelectedClub() {
            if (!state.selectedClubId) {
                showMessage("请先选择社团。", "error");
                return;
            }

            const currentClub = state.clubs.find(club => club.id === state.selectedClubId);
            if (!window.confirm(`确定要删除“${currentClub.name}”吗？该社团下的成员关联也会一起删除。`)) return;

            const fallbackClub = state.clubs.find(club => club.id !== state.selectedClubId);

            try {
                const data = await requestJson(`/api/clubs/${state.selectedClubId}`, { method: "DELETE" });
                showMessage(data.message || "社团已删除。");
                await refreshDashboard(fallbackClub ? fallbackClub.id : null);
            } catch (error) {
                showMessage(error.message, "error");
            }
        }

        document.getElementById("createClubBtn").addEventListener("click", async () => {
            const name = window.prompt("请输入新社团名称");
            if (!name) return;

            try {
                const data = await requestJson("/api/clubs", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: name.trim(), description: "", avatar: "" })
                });
                showMessage(data.message || "社团创建成功。");
                await refreshDashboard(data.club.id);
            } catch (error) {
                showMessage(error.message, "error");
            }
        });

        document.getElementById("refreshBtn").addEventListener("click", () => refreshDashboard(state.selectedClubId));
        document.getElementById("deleteClubBtn").addEventListener("click", deleteSelectedClub);

        document.getElementById("clubAvatarInput").addEventListener("change", async event => {
            try {
                state.pendingClubAvatar = await readFileAsDataUrl(event.target.files[0]);
            } catch (error) {
                showMessage(error.message, "error");
            }
        });

        document.getElementById("clubProfileForm").addEventListener("submit", async event => {
            event.preventDefault();

            if (!state.selectedClubId) {
                showMessage("请先选择社团。", "error");
                return;
            }

            const payload = {
                name: document.getElementById("clubNameInput").value.trim(),
                description: document.getElementById("clubDescriptionInput").value.trim()
            };

            if (state.pendingClubAvatar) {
                payload.avatar = state.pendingClubAvatar;
            }

            try {
                const data = await requestJson(`/api/clubs/${state.selectedClubId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                state.pendingClubAvatar = "";
                showMessage(data.message || "社团资料更新成功。");
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message, "error");
            }
        });

        document.getElementById("memberForm").addEventListener("submit", async event => {
            event.preventDefault();

            if (!state.selectedClubId) {
                showMessage("请先选择社团。", "error");
                return;
            }

            const formData = new FormData(event.target);
            const payload = {
                name: (formData.get("name") || "").trim(),
                student_id: (formData.get("student_id") || "").trim(),
                department: (formData.get("department") || "").trim(),
                role: formData.get("role")
            };

            try {
                const data = await requestJson(`/api/clubs/${state.selectedClubId}/members`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                event.target.reset();
                showMessage(data.message || "成员已添加到社团。");
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message, "error");
            }
        });

        refreshDashboard();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE_TEMPLATE)


def validate_role(role):
    return role in VALID_ROLES


@app.route("/api/clubs", methods=["GET"])
def get_clubs():
    clubs = Club.query.order_by(Club.created_at.desc()).all()
    return jsonify([club.to_dict() for club in clubs])


@app.route("/api/clubs", methods=["POST"])
def create_club():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    avatar = (data.get("avatar") or "").strip()

    if not name:
        return jsonify({"message": "请输入社团名称。"}), 400

    existing_club = Club.query.filter_by(name=name).first()
    if existing_club:
        return jsonify({"message": "该社团名称已存在，请更换名称。"}), 400

    club = Club(name=name, description=description, avatar=avatar)
    db.session.add(club)
    db.session.commit()
    return jsonify({"message": "社团创建成功。", "club": club.to_dict()}), 201


@app.route("/api/clubs/<int:club_id>", methods=["PUT"])
def update_club(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        return jsonify({"message": "未找到对应的社团。"}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    avatar = data.get("avatar")

    if not name:
        return jsonify({"message": "社团名称不能为空。"}), 400

    duplicated = Club.query.filter(Club.name == name, Club.id != club_id).first()
    if duplicated:
        return jsonify({"message": "该社团名称已被其他社团使用。"}), 400

    club.name = name
    club.description = description
    if avatar is not None:
        club.avatar = avatar.strip()

    db.session.commit()
    return jsonify({"message": "社团资料更新成功。", "club": club.to_dict()})


@app.route("/api/clubs/<int:club_id>", methods=["DELETE"])
def delete_club(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        return jsonify({"message": "未找到对应的社团。"}), 404

    db.session.delete(club)
    db.session.commit()
    return jsonify({"message": "社团已删除。"})


@app.route("/api/clubs/<int:club_id>/members", methods=["GET"])
def get_club_members(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        return jsonify({"message": "未找到对应的社团。"}), 404

    memberships = Membership.query.filter_by(club_id=club_id).order_by(Membership.created_at.desc()).all()
    return jsonify({
        "club": club.to_dict(),
        "memberships": [membership.to_dict() for membership in memberships],
    })


@app.route("/api/clubs/<int:club_id>/members", methods=["POST"])
def add_member_to_club(club_id):
    club = db.session.get(Club, club_id)
    if not club:
        return jsonify({"message": "未找到对应的社团。"}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    student_id = (data.get("student_id") or "").strip()
    department = (data.get("department") or "").strip()
    role = (data.get("role") or "队员").strip()

    if not name or not student_id or not department:
        return jsonify({"message": "请完整填写成员信息。"}), 400
    if not validate_role(role):
        return jsonify({"message": "职位不合法。"}), 400

    student = Student.query.filter_by(student_id=student_id).first()
    if student:
        if student.name != name or student.department != department:
            student.name = name
            student.department = department
    else:
        student = Student(name=name, student_id=student_id, department=department)
        db.session.add(student)
        db.session.flush()

    existing_membership = Membership.query.filter_by(student_id=student.id, club_id=club_id).first()
    if existing_membership:
        return jsonify({"message": "该成员已经在当前社团中。"}), 400

    membership = Membership(student_id=student.id, club_id=club_id, role=role)
    db.session.add(membership)
    db.session.commit()
    return jsonify({"message": "成员已成功加入社团。", "membership": membership.to_dict()}), 201


@app.route("/api/memberships/<int:membership_id>", methods=["PUT"])
def update_membership(membership_id):
    membership = db.session.get(Membership, membership_id)
    if not membership:
        return jsonify({"message": "未找到对应的社团成员记录。"}), 404

    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip()
    if not validate_role(role):
        return jsonify({"message": "职位不合法。"}), 400

    membership.role = role
    db.session.commit()
    return jsonify({"message": "成员职位更新成功。", "membership": membership.to_dict()})


@app.route("/api/memberships/<int:membership_id>", methods=["DELETE"])
def delete_membership(membership_id):
    membership = db.session.get(Membership, membership_id)
    if not membership:
        return jsonify({"message": "未找到对应的社团成员记录。"}), 404

    db.session.delete(membership)
    db.session.commit()
    return jsonify({"message": "成员已移出社团。"})


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
