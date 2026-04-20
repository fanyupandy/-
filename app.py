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
    <title>社团管理系统 Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        deep: '#081120',
                        neon: '#36e4da',
                        coral: '#ff7a90',
                        gold: '#f7c66a',
                        ink: '#dce7f5'
                    },
                    boxShadow: {
                        glow: '0 30px 80px rgba(3, 7, 18, 0.45)'
                    }
                }
            }
        };
    </script>
    <style>
        body {
            background:
                radial-gradient(circle at top left, rgba(54, 228, 218, 0.18), transparent 28%),
                radial-gradient(circle at bottom right, rgba(255, 122, 144, 0.18), transparent 28%),
                linear-gradient(135deg, #030712 0%, #0b1220 48%, #111827 100%);
            min-height: 100vh;
        }

        .glass {
            background: rgba(9, 16, 29, 0.74);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 30px 80px rgba(2, 6, 23, 0.32);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }

        .mesh::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(130deg, rgba(54, 228, 218, 0.1), transparent 36%),
                linear-gradient(320deg, rgba(255, 122, 144, 0.1), transparent 40%);
            pointer-events: none;
        }

        .scrollbar-thin::-webkit-scrollbar {
            width: 8px;
        }

        .scrollbar-thin::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.35);
            border-radius: 999px;
        }

        select option {
            color: #111827;
            background-color: #ffffff;
        }
    </style>
</head>
<body class="text-ink">
    <div class="min-h-screen xl:grid xl:grid-cols-[320px_1fr]">
        <aside class="mesh relative border-r border-white/10 bg-slate-950/80 px-6 py-8">
            <div class="relative z-10 flex h-full flex-col">
                <div>
                    <p class="text-xs uppercase tracking-[0.45em] text-neon/80">Club Manager</p>
                    <h1 class="mt-3 text-3xl font-black tracking-wide text-white">社团管理系统</h1>
                    <p class="mt-4 text-sm leading-7 text-slate-300">
                        支持创建社团、编辑社团简介、上传社团头像，并在社团内为每位成员分配队员、副社长或社长身份。
                    </p>
                </div>

                <div class="mt-8 grid grid-cols-2 gap-4">
                    <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <p class="text-xs uppercase tracking-[0.3em] text-slate-400">社团数量</p>
                        <p id="clubCount" class="mt-2 text-3xl font-bold text-white">0</p>
                    </div>
                    <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <p class="text-xs uppercase tracking-[0.3em] text-slate-400">成员总数</p>
                        <p id="totalMemberCount" class="mt-2 text-3xl font-bold text-white">0</p>
                    </div>
                </div>

                <div class="mt-8 flex items-center justify-between">
                    <h2 class="text-lg font-semibold text-white">社团列表</h2>
                    <button
                        id="openClubModalBtn"
                        class="rounded-xl bg-gradient-to-r from-neon to-coral px-4 py-2 text-sm font-semibold text-slate-950 transition hover:scale-[1.02]"
                    >
                        新建社团
                    </button>
                </div>

                <div id="clubList" class="scrollbar-thin mt-4 flex-1 space-y-3 overflow-y-auto pr-1">
                    <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-5 text-sm text-slate-400">
                        正在加载社团数据...
                    </div>
                </div>
            </div>
        </aside>

        <main class="px-4 py-6 sm:px-8 xl:px-10">
            <div class="mx-auto max-w-7xl space-y-6">
                <header class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <p class="text-sm uppercase tracking-[0.35em] text-slate-400">Professional Workspace</p>
                        <h2 class="mt-2 text-3xl font-bold text-white">社团资料与成员职位管理</h2>
                        <p class="mt-2 text-slate-300">
                            选择左侧社团后，可实时编辑社团资料，并在社团内部维护成员与职位。
                        </p>
                    </div>
                    <div class="flex flex-wrap gap-3">
                        <button
                            id="openMemberModalBtn"
                            class="rounded-xl border border-neon/40 bg-neon/10 px-4 py-3 text-sm font-semibold text-neon transition hover:bg-neon/20"
                        >
                            添加成员到当前社团
                        </button>
                        <button
                            id="refreshBtn"
                            class="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-slate-100 transition hover:bg-white/10"
                        >
                            刷新数据
                        </button>
                    </div>
                </header>

                <div id="messageBox" class="hidden rounded-2xl px-5 py-4 text-sm font-medium"></div>

                <section id="emptyState" class="glass rounded-[28px] p-10 text-center">
                    <div class="mx-auto max-w-2xl">
                        <p class="text-sm uppercase tracking-[0.35em] text-gold">Start Here</p>
                        <h3 class="mt-3 text-3xl font-bold text-white">先创建第一个社团</h3>
                        <p class="mt-4 text-base leading-7 text-slate-300">
                            创建社团后，你可以填写社团简介、上传头像，并将学生添加到该社团，同时设定他们在社团中的职位。
                        </p>
                    </div>
                </section>

                <div id="dashboardContent" class="hidden grid gap-6 2xl:grid-cols-[1.15fr_1fr]">
                    <section class="glass rounded-[28px] p-6">
                        <div class="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                            <div class="flex items-start gap-5">
                                <div class="relative h-24 w-24 overflow-hidden rounded-[24px] border border-white/10 bg-white/5">
                                    <img id="clubAvatarPreview" class="h-full w-full object-cover" src="" alt="社团头像">
                                    <div id="clubAvatarFallback" class="absolute inset-0 flex items-center justify-center text-3xl font-black text-white">
                                        社
                                    </div>
                                </div>
                                <div>
                                    <p class="text-sm uppercase tracking-[0.35em] text-neon/80">Club Profile</p>
                                    <h3 id="clubNameHeading" class="mt-2 text-3xl font-bold text-white">未选择社团</h3>
                                    <p id="clubMeta" class="mt-2 text-sm text-slate-400"></p>
                                </div>
                            </div>
                            <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                                <p class="text-xs uppercase tracking-[0.3em] text-slate-400">当前社团成员</p>
                                <p id="currentClubMemberCount" class="mt-2 text-3xl font-bold text-white">0</p>
                            </div>
                        </div>

                        <form id="clubProfileForm" class="mt-8 space-y-5">
                            <div>
                                <label class="mb-2 block text-sm font-medium text-slate-300">社团名称</label>
                                <input
                                    id="clubNameInput"
                                    name="name"
                                    type="text"
                                    required
                                    class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                                    placeholder="请输入社团名称"
                                >
                            </div>
                            <div>
                                <label class="mb-2 block text-sm font-medium text-slate-300">社团简介</label>
                                <textarea
                                    id="clubDescriptionInput"
                                    name="description"
                                    rows="5"
                                    class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                                    placeholder="介绍社团定位、活动方向与特色"
                                ></textarea>
                            </div>
                            <div>
                                <label class="mb-2 block text-sm font-medium text-slate-300">社团头像</label>
                                <input
                                    id="clubAvatarInput"
                                    type="file"
                                    accept="image/*"
                                    class="block w-full rounded-xl border border-dashed border-white/15 bg-white/5 px-4 py-3 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-neon/15 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-neon"
                                >
                                <p class="mt-2 text-xs text-slate-500">支持选择图片作为社团头像，保存后即时生效。</p>
                            </div>
                            <button
                                type="submit"
                                class="rounded-xl bg-gradient-to-r from-gold via-coral to-neon px-5 py-3 text-sm font-bold text-slate-950 transition hover:scale-[1.01]"
                            >
                                保存社团资料
                            </button>
                        </form>
                    </section>

                    <section class="glass rounded-[28px] p-6">
                        <div class="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                            <div>
                                <h3 class="text-2xl font-bold text-white">社团成员列表</h3>
                                <p class="mt-1 text-sm text-slate-400">为成员设置队员、副社长或社长，并支持一键移出社团。</p>
                            </div>
                        </div>

                        <div class="overflow-hidden rounded-2xl border border-white/10">
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-white/10">
                                    <thead class="bg-white/5">
                                        <tr class="text-left text-sm text-slate-300">
                                            <th class="px-5 py-4 font-medium">姓名</th>
                                            <th class="px-5 py-4 font-medium">学号</th>
                                            <th class="px-5 py-4 font-medium">院系</th>
                                            <th class="px-5 py-4 font-medium">职位</th>
                                            <th class="px-5 py-4 font-medium text-right">操作</th>
                                        </tr>
                                    </thead>
                                    <tbody id="memberTableBody" class="divide-y divide-white/5 bg-slate-950/10">
                                        <tr>
                                            <td colspan="5" class="px-5 py-10 text-center text-slate-400">请先选择一个社团。</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </main>
    </div>

    <div id="clubModal" class="fixed inset-0 z-50 hidden items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm">
        <div class="glass w-full max-w-xl rounded-[28px] p-6">
            <div class="mb-6 flex items-start justify-between gap-4">
                <div>
                    <p class="text-sm uppercase tracking-[0.35em] text-gold">New Club</p>
                    <h3 class="mt-2 text-2xl font-bold text-white">创建社团</h3>
                </div>
                <button data-close-modal="clubModal" class="rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/10">
                    关闭
                </button>
            </div>
            <form id="clubForm" class="space-y-4">
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">社团名称</label>
                    <input
                        name="name"
                        type="text"
                        required
                        class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                        placeholder="例如：摄影社"
                    >
                </div>
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">社团简介</label>
                    <textarea
                        name="description"
                        rows="4"
                        class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                        placeholder="简要介绍社团"
                    ></textarea>
                </div>
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">社团头像</label>
                    <input
                        id="newClubAvatarInput"
                        type="file"
                        accept="image/*"
                        class="block w-full rounded-xl border border-dashed border-white/15 bg-white/5 px-4 py-3 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-neon/15 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-neon"
                    >
                </div>
                <button
                    type="submit"
                    class="w-full rounded-xl bg-gradient-to-r from-neon to-coral px-4 py-3 text-sm font-bold text-slate-950 transition hover:scale-[1.01]"
                >
                    创建社团
                </button>
            </form>
        </div>
    </div>

    <div id="memberModal" class="fixed inset-0 z-50 hidden items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm">
        <div class="glass w-full max-w-xl rounded-[28px] p-6">
            <div class="mb-6 flex items-start justify-between gap-4">
                <div>
                    <p class="text-sm uppercase tracking-[0.35em] text-neon">New Member</p>
                    <h3 class="mt-2 text-2xl font-bold text-white">添加成员到社团</h3>
                </div>
                <button data-close-modal="memberModal" class="rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/10">
                    关闭
                </button>
            </div>
            <form id="memberForm" class="space-y-4">
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">姓名</label>
                    <input
                        name="name"
                        type="text"
                        required
                        class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                        placeholder="请输入成员姓名"
                    >
                </div>
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">学号</label>
                    <input
                        name="student_id"
                        type="text"
                        required
                        class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                        placeholder="请输入学号"
                    >
                </div>
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">院系</label>
                    <input
                        name="department"
                        type="text"
                        required
                        class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                        placeholder="例如：计算机学院"
                    >
                </div>
                <div>
                    <label class="mb-2 block text-sm font-medium text-slate-300">社团职位</label>
                    <select
                        name="role"
                        class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition focus:border-neon/50 focus:ring-2 focus:ring-neon/20"
                    >
                        <option value="队员" selected>队员</option>
                        <option value="副社长">副社长</option>
                        <option value="社长">社长</option>
                    </select>
                </div>
                <button
                    type="submit"
                    class="w-full rounded-xl bg-gradient-to-r from-gold via-coral to-neon px-4 py-3 text-sm font-bold text-slate-950 transition hover:scale-[1.01]"
                >
                    添加到社团
                </button>
            </form>
        </div>
    </div>

    <script>
        const roleOptions = ['队员', '副社长', '社长'];

        const state = {
            clubs: [],
            selectedClubId: null,
            selectedClub: null,
            memberships: [],
            pendingClubAvatar: '',
            pendingNewClubAvatar: ''
        };

        const messageBox = document.getElementById('messageBox');
        const clubList = document.getElementById('clubList');
        const clubCount = document.getElementById('clubCount');
        const totalMemberCount = document.getElementById('totalMemberCount');
        const currentClubMemberCount = document.getElementById('currentClubMemberCount');
        const memberTableBody = document.getElementById('memberTableBody');
        const emptyState = document.getElementById('emptyState');
        const dashboardContent = document.getElementById('dashboardContent');

        function showMessage(message, type = 'success') {
            messageBox.className = 'rounded-2xl px-5 py-4 text-sm font-medium';
            if (type === 'success') {
                messageBox.classList.add('bg-emerald-500/15', 'text-emerald-200', 'border', 'border-emerald-400/20');
            } else {
                messageBox.classList.add('bg-rose-500/15', 'text-rose-200', 'border', 'border-rose-400/20');
            }
            messageBox.textContent = message;
        }

        function hideMessage() {
            messageBox.className = 'hidden rounded-2xl px-5 py-4 text-sm font-medium';
            messageBox.textContent = '';
        }

        function toggleModal(id, show) {
            const modal = document.getElementById(id);
            modal.classList.toggle('hidden', !show);
            modal.classList.toggle('flex', show);
        }

        function initials(name) {
            return (name || '社').slice(0, 1);
        }

        function updateClubProfileView() {
            const avatarPreview = document.getElementById('clubAvatarPreview');
            const avatarFallback = document.getElementById('clubAvatarFallback');
            const heading = document.getElementById('clubNameHeading');
            const meta = document.getElementById('clubMeta');
            const nameInput = document.getElementById('clubNameInput');
            const descriptionInput = document.getElementById('clubDescriptionInput');

            if (!state.selectedClub) {
                emptyState.classList.remove('hidden');
                dashboardContent.classList.add('hidden');
                return;
            }

            emptyState.classList.add('hidden');
            dashboardContent.classList.remove('hidden');

            heading.textContent = state.selectedClub.name;
            meta.textContent = `创建时间：${state.selectedClub.created_at}`;
            nameInput.value = state.selectedClub.name || '';
            descriptionInput.value = state.selectedClub.description || '';
            currentClubMemberCount.textContent = state.selectedClub.member_count || 0;

            if (state.selectedClub.avatar) {
                avatarPreview.src = state.selectedClub.avatar;
                avatarPreview.classList.remove('hidden');
                avatarFallback.classList.add('hidden');
            } else {
                avatarPreview.src = '';
                avatarPreview.classList.add('hidden');
                avatarFallback.textContent = initials(state.selectedClub.name);
                avatarFallback.classList.remove('hidden');
            }
        }

        function renderClubList() {
            clubCount.textContent = state.clubs.length;
            totalMemberCount.textContent = state.clubs.reduce((sum, club) => sum + (club.member_count || 0), 0);

            if (!state.clubs.length) {
                clubList.innerHTML = `
                    <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-5 text-sm leading-6 text-slate-400">
                        还没有任何社团，点击“新建社团”开始搭建你的组织结构。
                    </div>
                `;
                return;
            }

            clubList.innerHTML = state.clubs.map(club => {
                const active = club.id === state.selectedClubId;
                return `
                    <button
                        onclick="selectClub(${club.id})"
                        class="w-full rounded-2xl border px-4 py-4 text-left transition ${
                            active
                                ? 'border-neon/40 bg-neon/10 shadow-lg'
                                : 'border-white/10 bg-white/5 hover:bg-white/10'
                        }"
                    >
                        <div class="flex items-center gap-4">
                            <div class="h-12 w-12 overflow-hidden rounded-2xl border border-white/10 bg-slate-900/80">
                                ${
                                    club.avatar
                                        ? `<img src="${club.avatar}" alt="${club.name}" class="h-full w-full object-cover">`
                                        : `<div class="flex h-full w-full items-center justify-center text-lg font-bold text-white">${initials(club.name)}</div>`
                                }
                            </div>
                            <div class="min-w-0 flex-1">
                                <p class="truncate font-semibold text-white">${club.name}</p>
                                <p class="mt-1 text-xs text-slate-400">${club.member_count || 0} 名成员</p>
                            </div>
                        </div>
                    </button>
                `;
            }).join('');
        }

        function renderMembers() {
            if (!state.selectedClub) {
                memberTableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-5 py-10 text-center text-slate-400">请先选择一个社团。</td>
                    </tr>
                `;
                return;
            }

            if (!state.memberships.length) {
                memberTableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-5 py-10 text-center text-slate-400">
                            当前社团还没有成员，点击上方按钮添加第一位成员。
                        </td>
                    </tr>
                `;
                return;
            }

            memberTableBody.innerHTML = state.memberships.map(item => `
                <tr class="transition hover:bg-white/5">
                    <td class="px-5 py-4 font-medium text-white">${item.student.name}</td>
                    <td class="px-5 py-4 text-slate-300">${item.student.student_id}</td>
                    <td class="px-5 py-4 text-slate-300">${item.student.department}</td>
                    <td class="px-5 py-4">
                        <select
                            onchange="updateMembershipRole(${item.id}, this.value)"
                            class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-neon/50"
                        >
                            ${roleOptions.map(role => `<option value="${role}" ${item.role === role ? 'selected' : ''}>${role}</option>`).join('')}
                        </select>
                    </td>
                    <td class="px-5 py-4 text-right">
                        <button
                            onclick="removeMembership(${item.id})"
                            class="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-200 transition hover:bg-rose-500/20"
                        >
                            移出社团
                        </button>
                    </td>
                </tr>
            `).join('');
        }

        async function readFileAsDataUrl(file) {
            if (!file) {
                return '';
            }
            return await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(new Error('图片读取失败'));
                reader.readAsDataURL(file);
            });
        }

        async function requestJson(url, options = {}) {
            const response = await fetch(url, options);
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || '请求失败');
            }
            return data;
        }

        async function loadClubs(preferredClubId = null) {
            const clubs = await requestJson('/api/clubs');
            state.clubs = clubs;

            if (!state.clubs.length) {
                state.selectedClubId = null;
                state.selectedClub = null;
                state.memberships = [];
                renderClubList();
                updateClubProfileView();
                renderMembers();
                return;
            }

            if (preferredClubId && state.clubs.some(club => club.id === preferredClubId)) {
                state.selectedClubId = preferredClubId;
            } else if (!state.selectedClubId || !state.clubs.some(club => club.id === state.selectedClubId)) {
                state.selectedClubId = state.clubs[0].id;
            }

            state.selectedClub = state.clubs.find(club => club.id === state.selectedClubId) || null;
            renderClubList();
            updateClubProfileView();
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
                showMessage(error.message || '加载数据失败。', 'error');
            }
        }

        async function selectClub(clubId) {
            state.selectedClubId = clubId;
            state.selectedClub = state.clubs.find(club => club.id === clubId) || null;
            renderClubList();
            updateClubProfileView();
            try {
                await loadMembers(clubId);
            } catch (error) {
                showMessage(error.message || '加载社团成员失败。', 'error');
            }
        }

        async function updateMembershipRole(membershipId, role) {
            try {
                const data = await requestJson(`/api/memberships/${membershipId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role })
                });
                showMessage(data.message || '职位更新成功。');
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message || '更新职位失败。', 'error');
            }
        }

        async function removeMembership(membershipId) {
            if (!window.confirm('确定要将该成员移出当前社团吗？')) {
                return;
            }

            try {
                const data = await requestJson(`/api/memberships/${membershipId}`, {
                    method: 'DELETE'
                });
                showMessage(data.message || '成员已移出社团。');
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message || '移出社团失败。', 'error');
            }
        }

        document.getElementById('openClubModalBtn').addEventListener('click', () => toggleModal('clubModal', true));
        document.getElementById('openMemberModalBtn').addEventListener('click', () => {
            if (!state.selectedClubId) {
                showMessage('请先创建并选择一个社团。', 'error');
                return;
            }
            toggleModal('memberModal', true);
        });
        document.getElementById('refreshBtn').addEventListener('click', () => refreshDashboard(state.selectedClubId));

        document.querySelectorAll('[data-close-modal]').forEach(button => {
            button.addEventListener('click', () => toggleModal(button.dataset.closeModal, false));
        });

        document.querySelectorAll('#clubModal, #memberModal').forEach(modal => {
            modal.addEventListener('click', event => {
                if (event.target === modal) {
                    toggleModal(modal.id, false);
                }
            });
        });

        document.getElementById('newClubAvatarInput').addEventListener('change', async event => {
            try {
                state.pendingNewClubAvatar = await readFileAsDataUrl(event.target.files[0]);
            } catch (error) {
                showMessage(error.message || '读取社团头像失败。', 'error');
            }
        });

        document.getElementById('clubAvatarInput').addEventListener('change', async event => {
            try {
                state.pendingClubAvatar = await readFileAsDataUrl(event.target.files[0]);
            } catch (error) {
                showMessage(error.message || '读取头像失败。', 'error');
            }
        });

        document.getElementById('clubForm').addEventListener('submit', async event => {
            event.preventDefault();
            hideMessage();

            const formData = new FormData(event.target);
            const payload = {
                name: (formData.get('name') || '').trim(),
                description: (formData.get('description') || '').trim(),
                avatar: state.pendingNewClubAvatar
            };

            try {
                const data = await requestJson('/api/clubs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                event.target.reset();
                state.pendingNewClubAvatar = '';
                toggleModal('clubModal', false);
                showMessage(data.message || '社团创建成功。');
                await refreshDashboard(data.club.id);
            } catch (error) {
                showMessage(error.message || '创建社团失败。', 'error');
            }
        });

        document.getElementById('clubProfileForm').addEventListener('submit', async event => {
            event.preventDefault();
            hideMessage();

            if (!state.selectedClubId) {
                showMessage('请先选择社团。', 'error');
                return;
            }

            const payload = {
                name: document.getElementById('clubNameInput').value.trim(),
                description: document.getElementById('clubDescriptionInput').value.trim()
            };

            if (state.pendingClubAvatar) {
                payload.avatar = state.pendingClubAvatar;
            }

            try {
                const data = await requestJson(`/api/clubs/${state.selectedClubId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                state.pendingClubAvatar = '';
                document.getElementById('clubAvatarInput').value = '';
                showMessage(data.message || '社团资料已更新。');
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message || '更新社团资料失败。', 'error');
            }
        });

        document.getElementById('memberForm').addEventListener('submit', async event => {
            event.preventDefault();
            hideMessage();

            if (!state.selectedClubId) {
                showMessage('请先选择社团。', 'error');
                return;
            }

            const formData = new FormData(event.target);
            const payload = {
                name: (formData.get('name') || '').trim(),
                student_id: (formData.get('student_id') || '').trim(),
                department: (formData.get('department') || '').trim(),
                role: formData.get('role')
            };

            try {
                const data = await requestJson(`/api/clubs/${state.selectedClubId}/members`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                event.target.reset();
                toggleModal('memberModal', false);
                showMessage(data.message || '成员已添加到社团。');
                await refreshDashboard(state.selectedClubId);
            } catch (error) {
                showMessage(error.message || '添加成员失败。', 'error');
            }
        });

        refreshDashboard();
    </script>
</body>
</html>
"""


def validate_role(role):
    return role in VALID_ROLES


@app.route("/")
def index():
    return render_template_string(PAGE_TEMPLATE)


@app.route("/api/students", methods=["GET"])
def get_students():
    students = Student.query.order_by(Student.join_date.desc()).all()
    return jsonify([student.to_dict() for student in students])


@app.route("/api/add", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    student_id = (data.get("student_id") or "").strip()
    department = (data.get("department") or "").strip()

    if not name or not student_id or not department:
        return jsonify({"message": "请完整填写姓名、学号和院系信息。"}), 400

    existing_student = Student.query.filter_by(student_id=student_id).first()
    if existing_student:
        return jsonify({"message": "该学号已存在，请使用唯一学号。"}), 400

    student = Student(name=name, student_id=student_id, department=department)
    db.session.add(student)
    db.session.commit()

    return jsonify({"message": "成员添加成功。", "student": student.to_dict()}), 201


@app.route("/api/delete/<int:id>", methods=["DELETE"])
def delete_student(id):
    student = db.session.get(Student, id)
    if not student:
        return jsonify({"message": "未找到对应的成员记录。"}), 404

    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": "成员删除成功。"})


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
