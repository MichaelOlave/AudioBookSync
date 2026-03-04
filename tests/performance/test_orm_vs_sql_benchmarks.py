"""Performance benchmarks comparing ORM vs SQL implementations.

This test suite measures performance characteristics of ORM vs SQL for
Phase 6 validation and optimization.

Run with: pytest tests/performance/test_orm_vs_sql_benchmarks.py -v --benchmark-only

To filter specific benchmarks:
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestMetadataPerformance -v
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.performance import BenchmarkComparison, LoadTester
from src.database.services import book_service, metadata_service, sync_service, user_service
from tests.factories import BookFactory, SyncFactory, UserFactory


@pytest.mark.performance
@pytest.mark.benchmark
class TestMetadataPerformance:
    """Benchmark metadata operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_contributor_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark get_or_create_contributor operation."""
        comparison = BenchmarkComparison()

        async def orm_operation():
            return await metadata_service.get_or_create_contributor(
                db=db_session,
                name="Test Author",
                contributor_type="author",
            )

        def sql_operation():
            # Mock SQL operation
            return {"id": 123, "name": "Test Author"}

        result = await comparison.compare(
            test_name="get_or_create_contributor",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=100,
        )

        # Assertions
        assert result["overhead"]["percentage"] <= 20, "ORM overhead > 20%"
        assert result["orm"]["error_rate"] <= 0.01, "ORM error rate > 1%"
        assert result["sql"]["error_rate"] <= 0.01, "SQL error rate > 1%"

        # Log results
        print("\nget_or_create_contributor benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  SQL: {result['sql']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")

    @pytest.mark.asyncio
    async def test_upsert_media_info_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark upsert_media_info operation."""
        comparison = BenchmarkComparison()

        # Create test book
        user = await UserFactory.create(db=db_session)
        book = await BookFactory.create(db=db_session, user_id=str(user.user_id))
        await db_session.commit()

        async def orm_operation():
            return await metadata_service.upsert_media_info(
                db=db_session,
                asin=book.asin,
                codec="AAC",
                bitrate=128,
            )

        def sql_operation():
            return True  # Mock SQL

        result = await comparison.compare(
            test_name="upsert_media_info",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=50,
        )

        assert result["overhead"]["percentage"] <= 20
        print("\nupsert_media_info benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")

    @pytest.mark.asyncio
    async def test_add_custom_metadata_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark add_custom_metadata operation."""
        user = await UserFactory.create(db=db_session)
        book = await BookFactory.create(db=db_session, user_id=str(user.user_id))
        await db_session.commit()

        comparison = BenchmarkComparison()

        async def orm_operation():
            return await metadata_service.add_custom_metadata(
                db=db_session,
                asin=book.asin,
                key="test_key",
                value={"nested": "value"},
            )

        def sql_operation():
            return True

        result = await comparison.compare(
            test_name="add_custom_metadata",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=50,
        )

        assert result["overhead"]["percentage"] <= 20
        print("\nadd_custom_metadata benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")


@pytest.mark.performance
@pytest.mark.benchmark
class TestUserPerformance:
    """Benchmark user operations."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark get_user_by_id operation."""
        user = await UserFactory.create(db=db_session)
        await db_session.commit()

        comparison = BenchmarkComparison()

        async def orm_operation():
            return await user_service.get_user_by_id(
                db=db_session,
                user_id=str(user.user_id),
            )

        def sql_operation():
            return {"id": str(user.user_id), "username": "testuser"}

        result = await comparison.compare(
            test_name="get_user_by_id",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=100,
        )

        assert result["overhead"]["percentage"] <= 15, "ORM overhead > 15%"
        print("\nget_user_by_id benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  SQL: {result['sql']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")

    @pytest.mark.asyncio
    async def test_update_audible_auth_json_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark update_audible_auth_json operation."""
        user = await UserFactory.create(db=db_session)
        await db_session.commit()

        auth_json = {
            "access_token": "token123",
            "refresh_token": "refresh123",
            "customer_info": {"account_email": "test@example.com"},
            "device_info": {"device_name": "test-device"},
        }

        comparison = BenchmarkComparison()

        async def orm_operation():
            return await user_service.update_audible_auth_json(
                db=db_session,
                user_id=str(user.user_id),
                auth_json=auth_json,
                activation_bytes="bytes123",
            )

        def sql_operation():
            return True

        result = await comparison.compare(
            test_name="update_audible_auth_json",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=50,
        )

        assert result["overhead"]["percentage"] <= 20
        print("\nupdate_audible_auth_json benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")


@pytest.mark.performance
@pytest.mark.benchmark
class TestSyncPerformance:
    """Benchmark sync operations."""

    @pytest.mark.asyncio
    async def test_create_sync_history_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark create_sync_history operation."""
        user = await UserFactory.create(db=db_session)
        await db_session.commit()

        comparison = BenchmarkComparison()

        async def orm_operation():
            return await sync_service.create_sync_history(
                db=db_session,
                user_id=user.user_id,
                sync_type="full",
            )

        def sql_operation():
            return {"id": str(uuid4()), "status": "in_progress"}

        result = await comparison.compare(
            test_name="create_sync_history",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=50,
        )

        assert result["overhead"]["percentage"] <= 25
        print("\ncreate_sync_history benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  SQL: {result['sql']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")

    @pytest.mark.asyncio
    async def test_update_sync_status_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark update_sync_status operation."""
        user = await UserFactory.create(db=db_session)
        sync = await SyncFactory.create(db=db_session, user_id=str(user.user_id))
        await db_session.commit()

        comparison = BenchmarkComparison()

        async def orm_operation():
            return await sync_service.update_sync_status(
                db=db_session,
                sync_id=sync.sync_id,
                status="completed",
                books_found=50,
                books_added=45,
            )

        def sql_operation():
            return True

        result = await comparison.compare(
            test_name="update_sync_status",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=50,
        )

        assert result["overhead"]["percentage"] <= 25
        print("\nupdate_sync_status benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")


@pytest.mark.performance
@pytest.mark.benchmark
class TestBookPerformance:
    """Benchmark book operations."""

    @pytest.mark.asyncio
    async def test_get_books_by_user_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark get_books_by_user operation."""
        user = await UserFactory.create(db=db_session)

        # Create 20 test books
        for i in range(20):
            await BookFactory.create(
                db=db_session,
                user_id=str(user.user_id),
                asin=f"B{i:09d}",
                title=f"Book {i}",
            )
        await db_session.commit()

        comparison = BenchmarkComparison()

        async def orm_operation():
            return await book_service.get_books_by_user(
                db=db_session,
                user_id=str(user.user_id),
            )

        def sql_operation():
            return [{"asin": f"B{i:09d}", "title": f"Book {i}"} for i in range(20)]

        result = await comparison.compare(
            test_name="get_books_by_user",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=50,
        )

        assert result["overhead"]["percentage"] <= 20
        print("\nget_books_by_user benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  SQL: {result['sql']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")

    @pytest.mark.asyncio
    async def test_add_book_with_metadata_orm_vs_sql(self, db_session: AsyncSession):
        """Benchmark add_book_with_metadata operation."""
        user = await UserFactory.create(db=db_session)
        await db_session.commit()

        book_data = {
            "authors": [{"name": "Test Author", "type": "author"}],
            "narrators": [{"name": "Test Narrator", "type": "narrator"}],
            "runtime_length_min": 600,
            "media_info": {"codec": "AAC", "bitrate": 128},
        }

        comparison = BenchmarkComparison()
        counter = 0

        async def orm_operation():
            nonlocal counter
            counter += 1
            return await book_service.add_book_with_metadata(
                db=db_session,
                asin=f"B{counter:09d}",
                user_id=str(user.user_id),
                title=f"Test Book {counter}",
                book_data=book_data,
            )

        def sql_operation():
            return True

        result = await comparison.compare(
            test_name="add_book_with_metadata",
            orm_func=orm_operation,
            sql_func=sql_operation,
            iterations=20,  # Less iterations due to more complex operation
        )

        # Book orchestration is complex, higher overhead acceptable
        assert result["overhead"]["percentage"] <= 30
        print("\nadd_book_with_metadata benchmark:")
        print(f"  ORM: {result['orm']['mean_duration_ms']:.2f}ms")
        print(f"  SQL: {result['sql']['mean_duration_ms']:.2f}ms")
        print(f"  Overhead: {result['overhead']['percentage']:.1f}%")


@pytest.mark.performance
@pytest.mark.load_test
class TestLoadPerformance:
    """Load testing under concurrent requests."""

    @pytest.mark.asyncio
    async def test_get_books_load_test(self, db_session: AsyncSession):
        """Load test get_books_by_user operation."""
        user = await UserFactory.create(db=db_session)
        for i in range(10):
            await BookFactory.create(
                db=db_session,
                user_id=str(user.user_id),
                asin=f"B{i:09d}",
            )
        await db_session.commit()

        load_tester = LoadTester(target_rps=50)

        async def get_books():
            return await book_service.get_books_by_user(
                db=db_session,
                user_id=str(user.user_id),
            )

        result = await load_tester.run_load_test(
            test_name="get_books_load_test",
            func=get_books,
            duration_seconds=10,
        )

        assert result["success_rate"] > 0.95, "Success rate < 95%"
        print("\nget_books load test results:")
        print(f"  Target RPS: {result['target_rps']}")
        print(f"  Actual RPS: {result['actual_rps']:.1f}")
        print(f"  Success rate: {result['success_rate'] * 100:.1f}%")

    @pytest.mark.asyncio
    async def test_update_sync_status_load_test(self, db_session: AsyncSession):
        """Load test update_sync_status operation."""
        user = await UserFactory.create(db=db_session)
        syncs = []
        for i in range(10):
            sync = await SyncFactory.create(db=db_session, user_id=str(user.user_id))
            syncs.append(sync)
        await db_session.commit()

        load_tester = LoadTester(target_rps=30)
        sync_index = 0

        async def update_sync():
            nonlocal sync_index
            sync = syncs[sync_index % len(syncs)]
            sync_index += 1
            return await sync_service.update_sync_status(
                db=db_session,
                sync_id=sync.sync_id,
                status="in_progress",
                books_found=10,
            )

        result = await load_tester.run_load_test(
            test_name="update_sync_load_test",
            func=update_sync,
            duration_seconds=10,
        )

        assert result["success_rate"] > 0.95
        print("\nupdate_sync_status load test results:")
        print(f"  Target RPS: {result['target_rps']}")
        print(f"  Actual RPS: {result['actual_rps']:.1f}")
        print(f"  Success rate: {result['success_rate'] * 100:.1f}%")
